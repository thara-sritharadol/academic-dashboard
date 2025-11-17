from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.papers_fetch import stream_papers_from_apis

class Command(BaseCommand):
    help = "Fetch papers automatically from CrossRef (and enrich with Semantic Scholar) and save to DB"

    def add_arguments(self, parser):
        parser.add_argument("--author", type=str, help="Author name to search")
        parser.add_argument("--query", type=str, help="Keyword or topic to search")
        parser.add_argument("--start", type=int, help="Start year")
        parser.add_argument("--end", type=int, help="End year")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If set, overwrite existing Paper records with fetched data (match by DOI)."
        )

    def handle(self, *args, **options):
        author = options.get("author")
        query = options.get("query")
        start_year = options.get("start")
        end_year = options.get("end")
        overwrite = options.get("overwrite", False)

        if not author and not query:
            self.stdout.write(self.style.ERROR("Please provide --author or --query"))
            return

        #Display search criteria to the user
        if author:
            self.stdout.write(self.style.NOTICE(f"Searching by author: {author} ({start_year}-{end_year})"))
        if query:
            self.stdout.write(self.style.NOTICE(f"Searching by keyword: {query} ({start_year}-{end_year})"))

        #Use the service to get a generator
        results_generator = stream_papers_from_apis(
            author=author,
            query=query,
            start_year=start_year,
            end_year=end_year
        )
        
        try:
            #The first item yielded by the generator is the total number of results
            total_results = next(results_generator)
        except StopIteration:
            total_results = 0

        if total_results == 0:
            self.stdout.write(self.style.WARNING("No papers found."))
            return

        self.stdout.write(self.style.NOTICE(f"Found available papers"))
        
        saved_count = 0
        updated_count = 0
        with tqdm(total=total_results, desc="Fetching & Saving", unit="paper", dynamic_ncols=True) as pbar:
            #Loop through the rest of the generator, which yields paper data
            for paper_data in results_generator:
                doi = paper_data.pop("doi", None)
                if not doi:
                    pbar.update(1) #Still update progress bar even if DOI is missing
                    continue

                #Handle Database Interaction
                if overwrite:
                    # Create or update the existing record
                    obj, created = Paper.objects.update_or_create(
                        doi=doi,
                        defaults=paper_data
                    )
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                else:
                    _, created = Paper.objects.get_or_create(
                        doi=doi,
                        defaults=paper_data
                    )
                    if created:
                        saved_count += 1

                pbar.set_postfix_str(f"Now: {paper_data.get('title', '')[:50]}...", refresh=True)
                pbar.update(1)

        msg = f"\nDone! New papers saved to DB: {saved_count}"
        if overwrite:
            msg += f", existing papers updated: {updated_count}"
        self.stdout.write(self.style.SUCCESS(msg))