from django.core.management.base import BaseCommand
from tqdm import tqdm
from api.models import Paper
from api.services.text_cleaning_service import TextCleaningService

class Command(BaseCommand):
    help = "Clean HTML/XML tags from all paper abstracts and titles in the database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Fetching papers with abstracts or titles..."))
        
        # Papers with Abstract or Title
        papers_query = Paper.objects.exclude(
            abstract__isnull=True, title__isnull=True
        ).exclude(
            abstract="", title=""
        )
        total_papers = papers_query.count()
        
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No papers found with abstracts or titles."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total_papers} papers. Starting cleaning process..."))

        updated_count = 0
        papers_to_update = []
        batch_size = 500

        for paper in tqdm(papers_query.iterator(), total=total_papers, desc="Cleaning Abstracts & Titles"):
            changed = False

            if paper.abstract:
                cleaned_abstract = TextCleaningService.clean_html_xml_tags(paper.abstract)
                if paper.abstract != cleaned_abstract:
                    paper.abstract = cleaned_abstract
                    changed = True

            if paper.title:
                cleaned_title = TextCleaningService.clean_html_xml_tags(paper.title)
                if paper.title != cleaned_title:
                    paper.title = cleaned_title
                    changed = True

            if changed:
                papers_to_update.append(paper)
                updated_count += 1

                if len(papers_to_update) >= batch_size:
                    Paper.objects.bulk_update(papers_to_update, ['abstract', 'title'])
                    papers_to_update = []

        if papers_to_update:
            Paper.objects.bulk_update(papers_to_update, ['abstract', 'title'])

        self.stdout.write(self.style.SUCCESS(
            f"\nCleaning Complete!\n"
            f"   - Total Papers Processed: {total_papers}\n"
            f"   - Papers Cleaned & Updated: {updated_count}"
        ))