import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm
from api.models import Paper, ClassifiedSubTopic, ClassifiedTopic
from api.services.topic_aggregator_service import TopicAggregator

class Command(BaseCommand):
    help = ("Aggregates sub-topics using Top-Down Gating and Bottom-Up Voting"
            " to create the final ClassifiedTopic list.")

    def add_arguments(self, parser):
        # --- การตั้งค่าหลัก ---
        parser.add_argument(
            "--model", 
            type=str, 
            default="allenai/specter2_base",
            help="Model name used for all embeddings."
        )
        parser.add_argument(
            "--l1-source",
            type=str,
            default="FoS_L1", # Source ของ L0-L1 embeddings (สำหรับ Pass 1)
            help="Source name for L0-L1 TopicEmbeddings (for Gating)."
        )
        
        # --- การตั้งค่าการกรอง (Filters) ---
        parser.add_argument(
            "--allowed-list-k",
            type=int,
            default=5,
            help="Top-K topics from Pass 1 (Top-Down) to use as the 'Allowed List'."
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.45, # (Noise Filter 1)
            help="Minimum confidence of sub-topics (evidence) to be included in voting."
        )
        parser.add_argument(
            "--max-ancestor-level",
            type=int,
            default=2, # (Noise Filter 2)
            help="Max level of ancestor topics to be included in voting (e.g., 2 = L0, L1, L2)."
        )
        parser.add_argument(
            "--min-vote-count",
            type=int,
            default=1, # (Noise Filter 3)
            help="Minimum number of votes required to save a final topic (e.g., 2 filters out 1-vote noise)."
        )

        # --- การตั้งค่าไฟล์ Map (ควรตรงกับที่วางไฟล์) ---
        parser.add_argument("--hierarchy-map", type=str, default="api/data/fos_hierarchy_map.json")
        parser.add_argument("--level-map", type=str, default="api/data/fos_level_map.json")

        # --- การกรอง Paper ---
        parser.add_argument("--start-year", type=int, help="Filter papers from this year.")
        parser.add_argument("--end-year", type=int, help="Filter papers up to this year.")
        parser.add_argument("--title", type=str, help="Filter papers by title (icontains).")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-process papers already in ClassifiedTopic."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        
        # 1. โหลด Service และเครื่องมือทั้งหมด
        try:
            aggregator = TopicAggregator(
                model_name=model_name,
                l1_source=options["l1_source"],
                hierarchy_map_path=options["hierarchy_map"],
                level_map_path=options["level_map"]
            )
            aggregator.stdout = lambda msg: self.stdout.write(msg)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error initializing aggregator: {e}"))
            return

        # 2. ดึง Papers ที่มี "หลักฐาน" (Sub-Topics) พร้อมประมวลผล
        self.stdout.write(self.style.NOTICE("Querying papers with sub-topic evidence..."))
        
        # หา Paper ID ทั้งหมดที่มี SubTopics
        paper_ids_with_evidence = ClassifiedSubTopic.objects.filter(
            embedding_model=model_name
        ).values_list('paper_id', flat=True).distinct()
        
        papers = Paper.objects.filter(id__in=paper_ids_with_evidence)

        # (Optional) กรอง Paper ตามที่ผู้ใช้สั่ง
        if options.get("start_year"):
            papers = papers.filter(year__gte=options["start_year"])
        if options.get("end_year"):
            papers = papers.filter(year__lte=options["end_year"])
        if options.get("title"):
            papers = papers.filter(title__icontains=options["title"])

        paper_ids_to_process = list(papers.values_list('id', flat=True))

        # 3. จัดการ Overwrite
        if options["overwrite"]:
            self.stdout.write(self.style.WARNING(
                f"OVERWRITE enabled. Deleting old final topics for {len(paper_ids_to_process):,} papers..."
            ))
            deleted_count, _ = ClassifiedTopic.objects.filter(
                paper_id__in=paper_ids_to_process,
                embedding_model=model_name
            ).delete()
            self.stdout.write(f"Deleted {deleted_count:,} old records.")
        else:
            # กรอง Paper ที่เคยประมวลผล (มี ClassifiedTopic) แล้วออก
            processed_paper_ids = ClassifiedTopic.objects.filter(
                embedding_model=model_name
            ).values_list('paper_id', flat=True).distinct()
            
            paper_ids_to_process = list(set(paper_ids_to_process) - set(processed_paper_ids))
            papers = papers.filter(id__in=paper_ids_to_process)

        total_papers = len(paper_ids_to_process)
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No new papers found to process."))
            return

        self.stdout.write(self.style.SUCCESS(f"📚 Found {total_papers:,} papers to aggregate.\n"))

        # 4. เริ่มการประมวลผล (เร็วมาก)
        processed_count = 0
        total_topics_saved = 0
        with tqdm(total=total_papers, desc="Aggregating Topics", unit="paper", dynamic_ncols=True) as pbar:
            
            # วนลูป Paper ที่ต้องประมวลผล
            for paper in papers.iterator():
                try:
                    # (Pass 1) สร้าง Allowed List
                    paper_text = f"{paper.title or ''}. {paper.abstract or ''}"
                    allowed_list = aggregator.get_allowed_list(
                        paper_text, 
                        k=options["allowed_list_k"]
                    )
                    
                    # (Pass 2) ดึงหลักฐาน
                    sub_topics = ClassifiedSubTopic.objects.filter(
                        paper=paper,
                        embedding_model=model_name,
                        confidence__gte=options["min_confidence"] # (Noise Filter 1)
                    )
                    
                    # (Gating) กรองและนับโหวต
                    final_votes = aggregator.get_filtered_votes(
                        sub_topics,
                        allowed_list,
                        max_ancestor_level=options["max_ancestor_level"], # (Noise Filter 2)
                        min_vote_count=options["min_vote_count"] # (Noise Filter 3)
                    )
                    
                    # (Save) บันทึกผลลัพธ์สุดท้าย
                    objs_to_create = []
                    for topic_name, votes in final_votes.items():
                        level = aggregator.level_map.get(topic_name)
                        l0_topic = aggregator.find_level_0_topic(topic_name)
                        objs_to_create.append(
                            ClassifiedTopic(
                                paper=paper,
                                topic_name=topic_name,
                                vote_count=votes,
                                level=level,
                                level_0_topic=l0_topic,
                                embedding_model=model_name
                            )
                        )
                    
                    if objs_to_create:
                        ClassifiedTopic.objects.bulk_create(objs_to_create, ignore_conflicts=True)
                        total_topics_saved += len(objs_to_create)

                    processed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"\nError aggregating paper {paper.id}: {e}"))
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Successfully aggregated {processed_count} papers and saved {total_topics_saved:,} final topics."
        ))