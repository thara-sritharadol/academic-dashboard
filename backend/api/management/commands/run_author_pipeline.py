#NOT USE!!!
import time
from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = ("Runs the full end-to-end skill profiling pipeline for a specific author: "
            "1. Fetch -> 2. Classify Sub-Skills -> 3. Aggregate Skills")

    def add_arguments(self, parser):
        parser.add_argument(
            "--author", 
            type=str, 
            required=True, 
            help="The full name of the author to process (e.g., 'Pokpong Songmuang')."
        )
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2",
            help="Model name to use for BOTH classifying and aggregating."
        )

        #for Fetch
        parser.add_argument("--start", type=int, help="Filter fetch: Start year.")
        parser.add_argument("--end", type=int, help="Filter fetch: End year.")

        #Aggregation (Adaptive Threshold & Gating)
        parser.add_argument(
            "--relative-threshold", 
            type=float, 
            default=0.85,
            help="[AGGREGATE] Select topics with score >= max_score * relative_threshold."
        )
        parser.add_argument(
            "--min-absolute-threshold", 
            type=float, 
            default=0.30,
            help="[AGGREGATE] Minimum absolute score required."
        )
        parser.add_argument(
            "--min-k", 
            type=int, 
            default=5,
            help="[AGGREGATE] Minimum number of topics in Allowed List (Safety Net)."
        )

        parser.add_argument(
            "--min-vote-count", type=int, default=2,
            help="[AGGREGATE] Minimum vote count to save a final skill."
        )
        parser.add_argument(
            "--min-level-to-save", type=int, default=0,
            help="[AGGREGATE] Minimum level to save (1 filters out L0)."
        )

    def handle(self, *args, **options):
        author_name = options['author']
        model_name = options['model']
        
        self.stdout.write(self.style.SUCCESS(f"--- STARTING PIPELINE for: {author_name} ---"))

        self.stdout.write(self.style.NOTICE(f"\n[Step 1/3] Fetching new papers from APIs..."))
        try:
            call_command(
                'fetch_papers',
                author=author_name,
                start=options.get('start'),
                end=options.get('end')
            )
            self.stdout.write(self.style.SUCCESS("[Step 1/3] Fetch complete."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[Step 1/3] Fetch FAILED: {e}"))
            return

        time.sleep(1)

        self.stdout.write(self.style.NOTICE(f"\n[Step 2/3] Classifying sub-skills (Evidence)..."))
        self.stdout.write(f"   (This step only processes NEW papers and is slow)")
        try:
            call_command(
                'classify_sub_skills',
                author=author_name,
                model=model_name,
            )
            self.stdout.write(self.style.SUCCESS("[Step 2/3] Sub-skill classification complete."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[Step 2/3] Classification FAILED: {e}"))
            return

        time.sleep(1)

        self.stdout.write(self.style.NOTICE(f"\n[Step 3/3] Aggregating final skill profile..."))
        self.stdout.write(f"   (This step is fast and recalculates the *entire* profile)")
        try:
            call_command(
                'aggregate_skills',
                author=author_name,
                model=model_name,
                relative_threshold=options['relative_threshold'],
                min_absolute_threshold=options['min_absolute_threshold'],
                min_k=options['min_k'],
                min_vote_count=options['min_vote_count'],
                min_level_to_save=options['min_level_to_save'],
                overwrite=True
            )
            self.stdout.write(self.style.SUCCESS("[Step 3/3] Aggregation complete."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[Step 3/3] Aggregation FAILED: {e}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"\n--- PIPELINE COMPLETE for: {author_name} ---"))