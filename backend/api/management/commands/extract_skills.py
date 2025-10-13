import time
from django.core.management.base import BaseCommand
from tqdm import tqdm
from api.models import Paper, ExtractedSkill
from api.services.skill_extraction import load_skill, SkillExtractor

class Command(BaseCommand):
    help = "Extract skills from paper abstracts using a predefined skill list and save them to the DB."

    def add_arguments(self, parser):

        parser.add_argument(
            "skills_file", 
            type=str, 
            help="Path to the skill dataset file (CSV or JSON)."
        )
        parser.add_argument(
            "--model", 
            type=str, 
            #default="all-MiniLM-L6-v2", 
            default="allenai/specter2_base",
            help="Name of the SentenceTransformer model to use."
        )
        parser.add_argument(
            "--top-k", 
            type=int, 
            default=20, 
            help="Number of top skills to extract for each paper."
        )
        parser.add_argument(
            "--author", 
            type=str, 
            help="Filter papers by a specific author name (case-insensitive contains)."
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
            help="Re-process papers that already have extracted skills.",
        )

    def handle(self, *args, **options):

        skills_file = options["skills_file"]
        model_name = options["model"]
        top_k = options["top_k"]
        author_filter = options.get("author")
        start_year = options.get("start_year")
        end_year = options.get("end_year")
        overwrite = options["overwrite"]

        # Load Skill List
        self.stdout.write(self.style.NOTICE(f"Loading skills from '{skills_file}'..."))
        try:
            skill_list = load_skill(skills_file)
        except (FileNotFoundError, ValueError) as e:
            self.stdout.write(self.style.ERROR(f"Error loading skills file: {e}"))
            return
        
        # Create SkillExtractor
        self.stdout.write(self.style.NOTICE(f"Initializing model '{model_name}' and creating embeddings..."))
        start_time = time.time()
        extractor = SkillExtractor(skill_list=skill_list, model_name=model_name)
        end_time = time.time()
        self.stdout.write(f"Initialization took {end_time - start_time:.2f} seconds.")

        # Fetch Papers from DB ---
        self.stdout.write(self.style.NOTICE("Querying papers from the database..."))
        papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract__exact='')

        # filter
        if author_filter:
            papers = papers.filter(authors__icontains=author_filter)
            self.stdout.write(f"   - Filtering by author: {author_filter}")
        if start_year:
            papers = papers.filter(year__gte=start_year)
            self.stdout.write(f"   - Filtering from year: {start_year}")
        if end_year:
            papers = papers.filter(year__lte=end_year)
            self.stdout.write(f"   - Filtering up to year: {end_year}")
            
        # if not overwrite, skip paper
        if not overwrite:
            papers = papers.exclude(extracted_skills__embedding_model=model_name)
            self.stdout.write(self.style.WARNING("   - Skipping papers already processed by this model. Use --overwrite to re-process."))

        total_papers = papers.count()
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No papers found matching the criteria to process."))
            return

        self.stdout.write(self.style.SUCCESS(f"📚 Found {total_papers} papers to process."))

        # process and save
        processed_count = 0
        with tqdm(total=total_papers, desc="Extracting Skills", unit="paper", dynamic_ncols=True) as pbar:
            # .iterator() for  memory save
            for paper in papers.iterator():
                extractor.extract_from_text(
                    paper=paper,
                    author_name=author_filter, # save author from filter
                    top_k=top_k,
                    save_to_db=True
                )
                processed_count += 1
                pbar.update(1)

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully processed {processed_count} papers and saved skills to the database."))