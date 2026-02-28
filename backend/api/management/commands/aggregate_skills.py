#NOT USE!!!
import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm
from api.models import Paper, ExtractedSubSkill, ExtractedSkill
from api.services.skill_aggregator_service import SkillAggregator

class Command(BaseCommand):
    help = ("Aggregates sub-skills using Top-Down Gating (Adaptive Threshold) and Bottom-Up Voting"
            " to create the final ClassifiedSkill list.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2",
            help="Model name used for all embeddings."
        )
        parser.add_argument(
            "--l1-source",
            type=str,
            default="FoS_L1",
            help="Source name for L0-L1 SkillEmbeddings (for Gating)."
        )
        
        parser.add_argument(
            "--relative-threshold",
            type=float,
            default=0.85,
            help="Select topics with score >= max_score * relative_threshold (Pass 1)."
        )
        parser.add_argument(
            "--min-absolute-threshold",
            type=float,
            default=0.30,
            help="Minimum absolute score required to be in Allowed List (Pass 1)."
        )
        parser.add_argument(
            "--min-k",
            type=int,
            default=5,
            help="Minimum number of topics in Allowed List (Safety Net)."
        )

        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.45,
            help="Minimum confidence of sub-skills (evidence) to be included in voting."
        )
        parser.add_argument(
            "--max-ancestor-level",
            type=int,
            default=2,
            help="Max level of ancestor skills to be included in voting (e.g., 2 = L0, L1, L2)."
        )
        parser.add_argument(
            "--min-vote-count",
            type=int,
            default=2,
            help="Minimum number of votes required to save a final skill (e.g., 2 filters out 1-vote noise)."
        )
        parser.add_argument(
            "--min-level-to-save",
            type=int,
            default=0,
            help="The minimum level of a skill to be saved (e.g., 1 filters out L0 skills)."
        )

        parser.add_argument("--hierarchy-map", type=str, default="api/data/fos_hierarchy_map.json")
        parser.add_argument("--level-map", type=str, default="api/data/fos_level_map.json")

        parser.add_argument("--start", type=int, help="Filter papers from this year.")
        parser.add_argument("--end", type=int, help="Filter papers up to this year.")
        parser.add_argument("--title", type=str, help="Filter papers by title (icontains).")
        parser.add_argument(
            "--author", 
            type=str, 
            help="Filter papers by author name (case-insensitive)."
        )
        
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-process papers already in ClassifiedSkill."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        
        try:
            aggregator = SkillAggregator(
                model_name=model_name,
                l1_source=options["l1_source"],
                hierarchy_map_path=options["hierarchy_map"],
                level_map_path=options["level_map"]
            )
            aggregator.stdout = lambda msg: self.stdout.write(msg)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error initializing aggregator: {e}"))
            return

        self.stdout.write(self.style.NOTICE("Querying papers with sub-skill evidence..."))
        
        paper_ids_with_evidence = ExtractedSubSkill.objects.filter(
            embedding_model=model_name
        ).values_list('paper_id', flat=True).distinct()
        
        papers = Paper.objects.filter(id__in=paper_ids_with_evidence)

        if options.get("start"):
            papers = papers.filter(year__gte=options["start"])
        if options.get("end"):
            papers = papers.filter(year__lte=options["end"])
        if options.get("title"):
            papers = papers.filter(title__icontains=options["title"])
            
        if options.get("author"):
            papers = papers.filter(authors__icontains=options["author"])
            self.stdout.write(f"   - Filtering by author: {options['author']}")

        paper_ids_to_process = list(papers.values_list('id', flat=True))

        if options["overwrite"]:
            self.stdout.write(self.style.WARNING(
                f"OVERWRITE enabled. Deleting old final skills for {len(paper_ids_to_process):,} papers..."
            ))
            deleted_count, _ = ExtractedSkill.objects.filter(
                paper_id__in=paper_ids_to_process,
                embedding_model=model_name
            ).delete()
            self.stdout.write(f"Deleted {deleted_count:,} old records.")
        else:
            processed_paper_ids = ExtractedSkill.objects.filter(
                embedding_model=model_name
            ).values_list('paper_id', flat=True).distinct()
            
            paper_ids_to_process = list(set(paper_ids_to_process) - set(processed_paper_ids))
            papers = papers.filter(id__in=paper_ids_to_process)

        total_papers = len(paper_ids_to_process)
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No new papers found to process."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_papers:,} papers to aggregate.\n"))

        processed_count = 0
        total_skills_saved = 0
        with tqdm(total=total_papers, desc="Aggregating Skills", unit="paper", dynamic_ncols=True) as pbar:
            
            for paper in papers.iterator():
                try:
                    paper_text = f"{paper.title or ''}. {paper.abstract or ''}"
                    
                    allowed_list = aggregator.get_allowed_list(
                        paper_text, 
                        relative_threshold=options["relative_threshold"],
                        min_absolute=options["min_absolute_threshold"],
                        min_k=options["min_k"]
                    )
                    
                    if options['verbosity'] > 1:
                        pbar.write(f"\n--- Paper: {paper.id} ({paper.title[:50]}...) ---")
                        pbar.write(f"   [Pass 1 Allowed List] (Adaptive): {', '.join(allowed_list) or 'None'}")
                    
                    sub_skills = ExtractedSubSkill.objects.filter(
                        paper=paper,
                        embedding_model=model_name,
                        confidence__gte=options["min_confidence"]
                    )
                    
                    final_votes = aggregator.get_filtered_votes(
                        sub_skills,
                        allowed_list,
                        max_ancestor_level=options["max_ancestor_level"],
                        min_vote_count=options["min_vote_count"],
                        min_level_to_save=options["min_level_to_save"]
                    )
                    
                    objs_to_create = []
                    for skill_name, votes in final_votes.items():
                        level = aggregator.level_map.get(skill_name)
                        l0_skill = aggregator.find_level_0_skill(skill_name)
                        objs_to_create.append(
                            ExtractedSkill(
                                paper=paper,
                                skill_name=skill_name,
                                vote_count=votes,
                                level=level,
                                level_0_skill=l0_skill,
                                embedding_model=model_name
                            )
                        )
                    
                    if objs_to_create:
                        ExtractedSkill.objects.bulk_create(objs_to_create, ignore_conflicts=True)
                        total_skills_saved += len(objs_to_create)

                    processed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"\nError aggregating paper {paper.id}: {e}"))
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully aggregated {processed_count} papers and saved {total_skills_saved:,} final skills."
        ))