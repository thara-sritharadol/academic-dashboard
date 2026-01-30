from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Author, Paper

class Command(BaseCommand):
    help = "Merge duplicate authors into a single primary author"

    def add_arguments(self, parser):
        #ID that want to keep
        parser.add_argument('--primary', type=str, required=True, help="OpenAlex ID of the primary author (Keep this one)")
        #Duplicates IDs
        parser.add_argument('--duplicates', nargs='+', required=True, help="List of OpenAlex IDs to merge into primary (These will be deleted)")

    def handle(self, *args, **options):
        primary_id = options['primary']
        duplicate_ids = options['duplicates']

        try:
            with transaction.atomic():
                # 1. find main authors
                try:
                    primary_author = Author.objects.get(openalex_id=primary_id)
                except Author.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Primary author {primary_id} not found!"))
                    return

                self.stdout.write(self.style.SUCCESS(f"Target Primary Author: {primary_author.name} ({primary_author.openalex_id})"))

                # 2. loop to find duplicate author
                for dup_id in duplicate_ids:
                    try:
                        dup_author = Author.objects.get(openalex_id=dup_id)
                    except Author.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Duplicate author {dup_id} not found, skipping."))
                        continue

                    if dup_author.id == primary_author.id:
                        continue

                    # 3. move all duplicate's paper to main author
                    papers = dup_author.papers.all()
                    count = papers.count()
                    
                    self.stdout.write(f"   > Merging {dup_author.name} ({dup_id}) with {count} papers...")

                    for paper in papers:
                        # add main to paper
                        paper.authors.add(primary_author)
                        # del duplicate
                        paper.authors.remove(dup_author)

                    # 4. del duplicate
                    dup_author.delete()
                    self.stdout.write(self.style.SUCCESS(f"     Successfully merged & deleted {dup_id}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during merge: {e}"))