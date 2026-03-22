import os
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Run the complete automated data pipeline (Fetch Authors -> Fetch Papers -> Deduplicate -> Clean -> Cluster)"

    def add_arguments(self, parser):
        # obtain the API key via the command line or retrieve it from environment variables.
        parser.add_argument("--tu_api_key", type=str, help="TU API Access Token")
        parser.add_argument("--faculty", type=str, help="TU Faculty")
        parser.add_argument("--gemini_key", type=str, help="Gemini API Key")
        parser.add_argument("--batch_size", type=int, default=50, help="Number of authors to fetch papers for")

    def handle(self, *args, **options):
        # 1. Manage API Keys (if not sent, retrieve them from the OS's Environment Variables).
        tu_api_key = options.get("tu_api_key") or os.environ.get("TU_API_KEY")
        tu_faculty = options.get("faculty")
        gemini_key = options.get("gemini_key") or os.environ.get("GEMINI_API_KEY")
        batch_size = options.get("batch_size")

        if not tu_api_key:
            self.stdout.write(self.style.ERROR("Error: TU API Key is required to run the pipeline."))
            return

        self.stdout.write(self.style.SUCCESS("=== Starting Daily Data Pipeline ==="))
        start_time = time.time()

        try:
            # ---------------------------------------------------------
            # Fetch Authors
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE("\n>>> Step 1: Fetching & Syncing TU Authors..."))
            call_command('sync_tu_authors', api_key=tu_api_key, faculty=tu_faculty)

            # ---------------------------------------------------------
            # Fetch Papers
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE(f"\n>>> Step 2: Fetching Papers (Batch Size: {batch_size})..."))
            call_command('batch_fetch_papers', batch_size=batch_size, faculty=tu_faculty)

            # ---------------------------------------------------------
            # Clean Abstracts
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE("\n>>> Step 3: Cleaning Abstracts (HTML/XML Tags)..."))
            call_command('clean_abstracts')

            # ---------------------------------------------------------
            # Deduplication (Merge Authors & Papers)
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE("\n>>> Step 4: Deduplicating Data..."))
            call_command('merge_authors')
            call_command('merge_papers')

            # ---------------------------------------------------------
            # Clustering (BERTopic + Gemini)
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE("\n>>> Step 5: Clustering & Auto-Naming Topics..."))
            if gemini_key:
                call_command('apply_bertopic_clusters', gemini_key=gemini_key)
            else:
                self.stdout.write(self.style.WARNING("No Gemini Key provided. Running clustering without LLM naming."))
                call_command('apply_bertopic_clusters')

            # ---------------------------------------------------------
            # Profiling (Argregate)
            # ---------------------------------------------------------
            self.stdout.write(self.style.NOTICE("\n>>> Step 6: Generating Author Profile..."))
            call_command('generate_author_profiles')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nPipeline failed due to an error: {e}"))
            return

        # Calculate the total time taken.
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Daily Pipeline Completed Successfully in {int(minutes)}m {int(seconds)}s! ==="
        ))