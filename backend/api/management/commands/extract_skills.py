import time
from django.core.management.base import BaseCommand
from tqdm import tqdm
from api.models import Paper
from api.services.skill_extraction import SkillExtractor

class Command(BaseCommand):
    help = "Extract skills from paper abstracts using skills stored in DB (with optional sentence splitting)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2",
            help="SentenceTransformer model name (must match SkillEmbedding in DB)."
        )
        parser.add_argument(
            "--top-k", 
            type=int, 
            default=10, 
            help="Number of top skills to extract for each paper."
        )
        parser.add_argument(
            "--author", 
            type=str, 
            help="Filter papers by author name (case-insensitive contains)."
        )
        parser.add_argument(
            "--start", 
            type=int, 
            help="Filter papers published from this year."
        )
        parser.add_argument(
            "--end", 
            type=int, 
            help="Filter papers published up to this year."
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-process papers already extracted by this model."
        )
        parser.add_argument(
            "--split",
            action="store_true",
            help="Enable sentence/paragraph splitting before embedding (improves confidence)."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        top_k = options["top_k"]
        author_filter = options.get("author")
        start_year = options.get("start")
        end_year = options.get("end")
        overwrite = options["overwrite"]
        use_split = options["split"]

        # ✅ แสดงสถานะเริ่มต้น
        self.stdout.write(self.style.NOTICE(
            f"Loading skills from DB (model={model_name})..."
        ))
        if use_split:
            self.stdout.write(self.style.WARNING("Sentence splitting: ENABLED"))
        else:
            self.stdout.write(self.style.SUCCESS("Sentence splitting: DISABLED"))

        # ✅ สร้าง SkillExtractor
        start_time = time.time()
        extractor = SkillExtractor(
            model_name=model_name,
            use_db=True,
            use_sentence_split=use_split,  # <<-- ใช้ flag ที่เพิ่มเข้ามา
        )
        end_time = time.time()
        self.stdout.write(f"Initialization took {end_time - start_time:.2f} seconds.\n")

        # ✅ ดึง papers จากฐานข้อมูล
        self.stdout.write(self.style.NOTICE("Querying papers from the database..."))
        papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract__exact="")

        if author_filter:
            papers = papers.filter(authors__icontains=author_filter)
            self.stdout.write(f"   - Filtering by author: {author_filter}")
        if start_year:
            papers = papers.filter(year__gte=start_year)
            self.stdout.write(f"   - From year: {start_year}")
        if end_year:
            papers = papers.filter(year__lte=end_year)
            self.stdout.write(f"   - Up to year: {end_year}")

        if not overwrite:
            papers = papers.exclude(extracted_skills__embedding_model=model_name)
            self.stdout.write(self.style.WARNING(
                "   - Skipping papers already processed by this model. Use --overwrite to re-process."
            ))

        total_papers = papers.count()
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No papers found matching the criteria."))
            return

        self.stdout.write(self.style.SUCCESS(f"📚 Found {total_papers} papers to process.\n"))

        # ✅ เริ่มการประมวลผล
        processed_count = 0
        with tqdm(total=total_papers, desc="Extracting Skills", unit="paper", dynamic_ncols=True) as pbar:
            for paper in papers.iterator():
                extractor.extract_from_text(
                    paper=paper,
                    author_name=author_filter,
                    top_k=top_k,
                    save_to_db=True,
                )
                processed_count += 1
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Successfully processed {processed_count} papers and saved extracted skills."
        ))
