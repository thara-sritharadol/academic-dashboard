import time
import requests
from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Paper, Author
from api.services.papers_fetch import stream_papers_from_apis

class Command(BaseCommand):
    help = "Fetch papers automatically from CrossRef/OpenAlex and save to DB with Author relations and Concepts"

    def add_arguments(self, parser):
        parser.add_argument("--author", type=str, help="Author name to search")
        parser.add_argument("--query", type=str, help="Keyword or topic to search")
        parser.add_argument("--start", type=int, help="Start year")
        parser.add_argument("--end", type=int, help="End year")
        parser.add_argument(
            "--source", 
            type=str, 
            default="openalex", 
            choices=["crossref", "openalex"],
            help="Source API to fetch from (default: openalex)"
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If set, overwrite existing Paper records with fetched data."
        )

    def handle(self, *args, **options):
        author = options.get("author")
        query = options.get("query")
        start_year = options.get("start")
        end_year = options.get("end")
        overwrite = options.get("overwrite", False)
        source = options.get("source")

        if not author and not query:
            self.stdout.write(self.style.ERROR("Please provide --author or --query"))
            return

        if author:
            self.stdout.write(self.style.NOTICE(f"Searching by author: {author} ({start_year}-{end_year})"))
        if query:
            self.stdout.write(self.style.NOTICE(f"Searching by keyword: {query} ({start_year}-{end_year})"))
        self.stdout.write(self.style.NOTICE(f"Fetching from source: {source}"))

        results_generator = stream_papers_from_apis(
            author=author,
            query=query,
            start_year=start_year,
            end_year=end_year,
            source=source
        )
        
        try:
            total_results = next(results_generator)
        except StopIteration:
            total_results = 0

        if total_results == 0:
            self.stdout.write(self.style.WARNING("No papers found."))
            return

        self.stdout.write(self.style.NOTICE(f"Found available papers, starting download..."))
        
        headers = {
            'User-Agent': 'mailto:thara.sri@dome.tu.ac.th' 
        }

        saved_count = 0
        updated_count = 0
        
        with tqdm(total=total_results, desc="Fetching & Saving", unit="paper", dynamic_ncols=True) as pbar:
            for paper_data in results_generator:
                doi = paper_data.pop("doi", None)
                if not doi:
                    pbar.update(1)
                    continue

                # Separate the Authors information
                authors_struct = paper_data.pop("authors_struct", [])
                
                # Save and Update Paper
                if overwrite:
                    paper_obj, created = Paper.objects.update_or_create(
                        doi=doi,
                        defaults=paper_data
                    )
                else:
                    paper_obj, created = Paper.objects.get_or_create(
                        doi=doi,
                        defaults=paper_data
                    )

                if created:
                    saved_count += 1
                else:
                    if overwrite:
                        updated_count += 1
                
                # 2Handle Many-to-Many Authors
                if overwrite:
                    paper_obj.authors.clear()

                for auth_data in authors_struct:
                    name = auth_data.get("name")
                    oa_id = auth_data.get("openalex_id")
                    
                    if not name:
                        continue

                    author_obj = None
                    if oa_id:
                        author_obj, _ = Author.objects.get_or_create(
                            openalex_id=oa_id,
                            defaults={"name": name}
                        )
                    else:
                        # If no openalex_id, find by name (use first if duplicates exist)
                        author_obj = Author.objects.filter(name=name).first()
                        if not author_obj:
                            author_obj = Author.objects.create(name=name)
                    
                    if author_obj:
                        paper_obj.authors.add(author_obj)

                # 3. Fetch Concepts from OpenAlex directly
                doi_str = doi.strip()
                if not doi_str.startswith('http'):
                    doi_url = f"https://doi.org/{doi_str}"
                else:
                    doi_url = doi_str
                api_url = f"https://api.openalex.org/works/{doi_url}"

                try:
                    response = requests.get(api_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        concepts = [
                            {
                                'id': c.get('id'),
                                'name': c.get('display_name'),
                                'level': c.get('level'),
                                'score': c.get('score')
                            }
                            for c in data.get('concepts', [])
                        ]
                        
                        # บันทึก concepts ลง Database ทันที
                        paper_obj.openalex_concepts = concepts
                        paper_obj.save(update_fields=['openalex_concepts'])
                        
                except Exception as e:
                    # ปริ้นท์ error ไว้ข้างล่าง progress bar
                    tqdm.write(f"\nError fetching concepts for {doi}: {str(e)}")

                # Sleep
                time.sleep(0.1)

                pbar.set_postfix_str(f"Now: {paper_data.get('title', '')[:30]}...", refresh=True)
                pbar.update(1)

        msg = f"\nDone! New papers: {saved_count}"
        if overwrite:
            msg += f", Updated: {updated_count}"
        self.stdout.write(self.style.SUCCESS(msg))