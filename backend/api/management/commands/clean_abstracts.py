from django.core.management.base import BaseCommand
from tqdm import tqdm
from api.models import Paper
from api.services.text_cleaning_service import TextCleaningService

class Command(BaseCommand):
    help = "Clean HTML/XML tags from all paper abstracts in the database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Fetching papers with abstracts..."))
        
        # Paper with Abstract
        papers_query = Paper.objects.exclude(abstract__isnull=True).exclude(abstract="")
        total_papers = papers_query.count()
        
        if total_papers == 0:
            self.stdout.write(self.style.WARNING("No papers found with abstracts."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total_papers} papers. Starting cleaning process..."))

        updated_count = 0
        papers_to_update = []
        batch_size = 500 # Save into DB

        for paper in tqdm(papers_query.iterator(), total=total_papers, desc="Cleaning Abstracts"):
            original_abstract = paper.abstract
            cleaned_abstract = TextCleaningService.clean_html_xml_tags(original_abstract)
            
            # If the text changes after cleaning (it means that junk tags have been removed).
            if original_abstract != cleaned_abstract:
                paper.abstract = cleaned_abstract
                papers_to_update.append(paper)
                updated_count += 1
                
                # If the accumulated batch size is reached, send the updates to the database all at once.
                if len(papers_to_update) >= batch_size:
                    Paper.objects.bulk_update(papers_to_update, ['abstract'])
                    papers_to_update = [] # Clear list

        # Update the remainders from batch_size division that don't result in a perfect division.
        if papers_to_update:
            Paper.objects.bulk_update(papers_to_update, ['abstract'])

        self.stdout.write(self.style.SUCCESS(
            f"\nCleaning Complete!\n"
            f"   - Total Papers Processed: {total_papers}\n"
            f"   - Abstracts Cleaned & Updated: {updated_count}"
        ))