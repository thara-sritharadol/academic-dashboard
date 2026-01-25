from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Paper, Author  # Import Author Model เพิ่มเข้ามา
from api.services.papers_fetch import stream_papers_from_apis

class Command(BaseCommand):
    help = "Fetch papers automatically from CrossRef/OpenAlex and save to DB with Author relations"

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
        
        saved_count = 0
        updated_count = 0
        
        with tqdm(total=total_results, desc="Fetching & Saving", unit="paper", dynamic_ncols=True) as pbar:
            for paper_data in results_generator:
                doi = paper_data.pop("doi", None)
                if not doi:
                    pbar.update(1)
                    continue

                # --- 1. แยกข้อมูล Authors (list of dicts) ออกมาก่อน ---
                # ต้อง pop ออก เพราะ field 'authors_struct' ไม่มีจริงใน Model Paper
                authors_struct = paper_data.pop("authors_struct", [])
                
                # --- 2. Save/Update Paper ---
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
                
                # --- 3. Handle Many-to-Many Authors ---
                # ถ้า overwrite เราอาจจะอยาก clear authors เก่าก่อน เพื่อความชัวร์
                if overwrite:
                    paper_obj.authors.clear()

                for auth_data in authors_struct:
                    name = auth_data.get("name")
                    oa_id = auth_data.get("openalex_id")
                    
                    if not name:
                        continue

                    # Logic: พยายามหาจาก OpenAlex ID ก่อน (แม่นยำสุด) ถ้าไม่มีให้หาจากชื่อ
                    author_obj = None
                    
                    if oa_id:
                        author_obj, _ = Author.objects.get_or_create(
                            openalex_id=oa_id,
                            defaults={"name": name}
                        )
                    else:
                        # Fallback สำหรับ CrossRef หรือข้อมูลที่ไม่มี ID
                        author_obj, _ = Author.objects.get_or_create(
                            name=name
                        )
                    
                    # เชื่อมความสัมพันธ์
                    if author_obj:
                        paper_obj.authors.add(author_obj)

                pbar.set_postfix_str(f"Now: {paper_data.get('title', '')[:30]}...", refresh=True)
                pbar.update(1)

        msg = f"\nDone! New papers: {saved_count}"
        if overwrite:
            msg += f", Updated: {updated_count}"
        self.stdout.write(self.style.SUCCESS(msg))