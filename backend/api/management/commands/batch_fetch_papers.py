import time
from datetime import timedelta
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from api.models import Paper, Author
from api.services.papers_fetch import stream_papers_from_apis

class Command(BaseCommand):
    help = "Batch fetch papers for authors in the database (processes those with oldest fetch dates first)"

    def add_arguments(self, parser):
        # Specify how many professors' papers to retrieve in this run (to prevent the run from taking too long).
        parser.add_argument("--batch_size", type=int, default=50, help="Number of authors to process in this run")
        parser.add_argument("--faculty", type=str, help="Filter authors by a specific faculty")
        parser.add_argument("--source", type=str, default="openalex", choices=["crossref", "openalex"])
        # The option to force a re-pull for those who have recently pulled.
        parser.add_argument("--force_refresh", action="store_true", help="Fetch papers even if recently fetched")

    def handle(self, *args, **options):
        batch_size = options.get("batch_size")
        faculty_filter = options.get("faculty")
        source = options.get("source")
        force_refresh = options.get("force_refresh")

        # Queue Logic
        queryset = Author.objects.exclude(faculty__isnull=True).exclude(faculty__exact="")
        
        if faculty_filter:
            queryset = queryset.filter(faculty__icontains=faculty_filter)

        if not force_refresh:
            # Assuming that data was retrieved within the last 30 days, it will not be retrieved again to save API input.
            thirty_days_ago = timezone.now() - timedelta(days=30)
            # Only include those who have never retrieved (isnull=True) or have retrieved more than 30 days ago.
            # .exclude(last_fetched_papers__gt=thirty_days_ago)
            # Sort by placing those with `last_fetched_papers` as Null first (asc nulls_first).
            queryset = queryset.exclude(last_fetched_papers__gt=thirty_days_ago)

        # The process is queued by starting with the oldest (or never-before-used) task, and then cuts the data according to the batch_size.
        authors_to_process = queryset.order_by(F('last_fetched_papers').asc(nulls_first=True))[:batch_size]

        if not authors_to_process:
            self.stdout.write(self.style.SUCCESS("No authors need updating at this time. Everything is up to date!"))
            return

        self.stdout.write(self.style.NOTICE(f"Starting batch fetch for {len(authors_to_process)} authors..."))

        total_papers_saved = 0

        for author in tqdm(authors_to_process, desc="Fetching Papers", unit="author"):
            author_name = author.name
            
            # Use existing function to retrieve the paper.
            results_generator = stream_papers_from_apis(
                author=author_name,
                source=source
            )
            
            try:
                total_results = next(results_generator)
            except StopIteration:
                total_results = 0

            # If a paper is found, the loop continues to record it.
            if total_results > 0:
                for paper_data in results_generator:
                    doi = paper_data.pop("doi", None)
                    if not doi: continue
                    
                    authors_struct = paper_data.pop("authors_struct", [])
                    # Note: openalex_concepts will be automatically saved to DB since it remains in paper_data
                    
                    # save Paper into DB
                    paper_obj, p_created = Paper.objects.update_or_create(
                        doi=doi,
                        defaults=paper_data
                    )
                    if p_created:
                        total_papers_saved += 1
                        
                    # Many-to-Many
                    paper_obj.authors.add(author)
                    
                    # Manage co-authors slightly (no need for detailed creation to reduce bottlenecks).
                    for auth_data in authors_struct:
                        co_name = auth_data.get("name")
                        co_oa_id = auth_data.get("openalex_id")

                        if not co_name:
                            continue

                        if co_name.lower() == author_name.lower():
                            if co_oa_id and not author.openalex_id:
                                # Check if this openalex_id is already assigned to another author
                                if not Author.objects.filter(openalex_id=co_oa_id).exclude(pk=author.pk).exists():
                                    author.openalex_id = co_oa_id

                        else:
                            co_author_obj = None
                            
                            # If an OpenAlex ID is provided, use that ID as the primary reference for searching or creating a new one.
                            if co_oa_id:
                                co_author_obj, _ = Author.objects.get_or_create(
                                    openalex_id=co_oa_id,
                                    defaults={"name": co_name}
                                )
                            else:
                                # If there is no ID, search by name (use iexact to ignore case sensitivity).
                                co_author_obj = Author.objects.filter(name__iexact=co_name).first()
                                if not co_author_obj:
                                    co_author_obj = Author.objects.create(name=co_name)
                                    
                            paper_obj.authors.add(co_author_obj)

            # The timestamp indicates that this professor has finished updating the paper.
            author.last_fetched_papers = timezone.now()
            author.save(update_fields=['last_fetched_papers', 'openalex_id'])
            
            time.sleep(1.5)

        self.stdout.write(self.style.SUCCESS(
            f"\nBatch Process Complete!\n"
            f"   - Authors Processed: {len(authors_to_process)}\n"
            f"   - New Papers Discovered: {total_papers_saved}"
        ))