import time
from django.core.management.base import BaseCommand
from tqdm import tqdm
from api.models import Paper
# ## CHANGED ##: Import the new TopicClassifier
from api.services.topic_classifier import TopicClassifier

class Command(BaseCommand):
    help = "Classify topics for paper abstracts using TopicEmbeddings stored in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2",
            help="SentenceTransformer model name (must match TopicEmbedding in DB)."
        )
        parser.add_argument(
            "--top-k", 
            type=int, 
            default=3, 
            help="Number of top topics to classify for each paper."
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.4,
            help="Minimum confidence score to save a topic."
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
            help="Re-classify papers that have already been processed by this model."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        top_k = options["top_k"]
        threshold = options["threshold"]
        start_year = options.get("start")
        end_year = options.get("end")
        overwrite = options["overwrite"]

        self.stdout.write(self.style.NOTICE(
            f"🤖 Initializing TopicClassifier (model={model_name})..."
        ))
        
        start_time = time.time()
        try:
            # ## CHANGED ##: Use TopicClassifier
            classifier = TopicClassifier(model_name=model_name)
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            return
            
        end_time = time.time()
        self.stdout.write(f"Initialization took {end_time - start_time:.2f} seconds.\n")

        self.stdout.write(self.style.NOTICE("Querying papers from the database..."))
        papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract__exact="")

        # Apply filters
        if start_year:
            papers = papers.filter(year__gte=start_year)
            self.stdout.write(f"   - Filtering from year: {start_year}")
        if end_year:
            papers = papers.filter(year__lte=end_year)
            self.stdout.write(f"   - Filtering up to year: {end_year}")

        if not overwrite:
            # ## CHANGED ##: Check against 'classified_topics' relation
            papers = papers.exclude(classified_topics__embedding_model=model_name)
            self.stdout.write(self.style.WARNING(
                "   - Skipping papers already processed. Use --overwrite to re-process."
            ))

        total_papers = papers.count()
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No papers found matching the criteria."))
            return

        self.stdout.write(self.style.SUCCESS(f"📚 Found {total_papers:,} papers to process.\n"))

        processed_count = 0
        with tqdm(total=total_papers, desc="Classifying Topics", unit="paper", dynamic_ncols=True) as pbar:
            # Use iterator() for memory efficiency with large datasets
            for paper in papers.iterator():
                # ## CHANGED ##: Call the classify_paper method
                classifier.classify_paper(
                    paper=paper,
                    top_k=top_k,
                    confidence_threshold=threshold,
                    save_to_db=True,
                )
                processed_count += 1
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 Successfully processed {processed_count:,} papers and saved classified topics."
        ))