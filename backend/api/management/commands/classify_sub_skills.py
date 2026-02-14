import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm
from api.models import Paper, ExtractedSubSkill
from api.services.sub_skill_classifier import SubSkillClassifier

class Command(BaseCommand):
    help = ("Classifies each sentence of a paper abstract against all skills"
            " and saves the results (sub-Skills) to the database as 'evidence'.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2",
            help="SentenceTransformer model name (must match SkillEmbedding)."
        )
        parser.add_argument(
            "--source",
            type=str,
            default="FoS_Base", 
            help="The 'source' name of the SkillEmbedding set to use."
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.45, 
            help="Minimum confidence threshold to save a sub-skills."
        )
        parser.add_argument(
            "--start", type=int, help="Filter papers published from this year."
        )
        parser.add_argument(
            "--end", type=int, help="Filter papers published up to this year."
        )
        parser.add_argument(
            "--author", type=str, help="Filter papers by author name (case-insensitive)."
        )
        
        parser.add_argument(
            "--title", type=str, help="Filter papers by title (case-insensitive contains)."
        )
        
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-process papers already processed by this model."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        source = options["source"]
        threshold = options["threshold"]
        overwrite = options["overwrite"]

        #Load Model and Skill Embeddings
        try:
            classifier = SubSkillClassifier(model_name=model_name, source=source)
            classifier.stdout = lambda msg: self.stdout.write(msg) 
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Error initializing classifier: {e}"))
            return

        #Fetch Paper from DB
        self.stdout.write(self.style.NOTICE("Querying papers from the database..."))
        papers = Paper.objects.filter(
            Q(abstract__isnull=False) & ~Q(abstract__exact='')
        )

        if options.get("start"):
            papers = papers.filter(year__gte=options["start"])
            self.stdout.write(f"   - Filtering from year: {options['start']}")
        if options.get("end"):
            papers = papers.filter(year__lte=options["end"])
            self.stdout.write(f"   - Filtering up to year: {options['end']}")
        if options.get("author"):
            papers = papers.filter(authors__icontains=options["author"])
            self.stdout.write(f"   - Filtering by author: {options['author']}")
            
        if options.get("title"):
            papers = papers.filter(title__icontains=options["title"])
            self.stdout.write(f"   - Filtering by title: {options['title']}")

        paper_ids_to_process = list(papers.values_list('id', flat=True))

        #Handle Overwrite
        if overwrite:
            self.stdout.write(self.style.WARNING(
                f"OVERWRITE enabled. Deleting old sub-skills for {len(paper_ids_to_process):,} papers..."
            ))
            deleted_count, _ = ExtractedSubSkill.objects.filter(
                paper_id__in=paper_ids_to_process,
                embedding_model=model_name
            ).delete()
            self.stdout.write(f"Deleted {deleted_count:,} old records.")
        else:
            processed_paper_ids = ExtractedSubSkill.objects.filter(
                embedding_model=model_name
            ).values_list('paper_id', flat=True).distinct()
            
            paper_ids_to_process = list(set(paper_ids_to_process) - set(processed_paper_ids))
            papers = papers.filter(id__in=paper_ids_to_process)
            self.stdout.write(self.style.WARNING(
                "Skipping papers already processed. Use --overwrite to re-process."
            ))

        total_papers = len(paper_ids_to_process)
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No new papers found to process."))
            return

        self.stdout.write(self.style.SUCCESS(f"📚 Found {total_papers:,} papers to process.\n"))

        processed_count = 0
        with tqdm(total=total_papers, desc="Classifying Sub-Skills", unit="paper", dynamic_ncols=True) as pbar:
            for paper in papers.iterator():
                try:
                    classifier.classify_paper_sentences(
                        paper=paper,
                        confidence_threshold=threshold
                    )
                    processed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"\nError processing paper {paper.id}: {e}"))
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully processed {processed_count} papers and saved sub-skill evidence."
        ))