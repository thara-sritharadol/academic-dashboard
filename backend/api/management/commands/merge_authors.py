from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower
from api.models import Author

class Command(BaseCommand):
    help = "Merge duplicate authors based on exact case-insensitive name matching"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Scanning for duplicate authors..."))

        # Find duplicate names (case-insensitive).
        duplicates = (
            Author.objects.annotate(name_lower=Lower('name'))
            .values('name_lower')
            .annotate(name_count=Count('id'))
            .filter(name_count__gt=1)
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate authors found!"))
            return

        total_merged = 0
        total_deleted = 0

        # Merge
        for dup in duplicates:
            name_lower = dup['name_lower']
            
            # Pull up all duplicate lists (sorted by who has the most papers or who has faculty as the primary reference).
            matching_authors = list(Author.objects.filter(name__iexact=name_lower).order_by('-faculty'))
            
            # Let the first person be the "primary draft".
            primary_author = matching_authors[0]
            duplicates_to_merge = matching_authors[1:]
            
            for duplicate in duplicates_to_merge:
                # Transfer all papers from the clone draft to the original draft.
                for paper in duplicate.papers.all():
                    paper.authors.add(primary_author)
                    paper.authors.remove(duplicate)
                
                # If the clone has an openalex_id but the original doesn't, transfer the ID as well.
                if duplicate.openalex_id and not primary_author.openalex_id:
                    primary_author.openalex_id = duplicate.openalex_id
                    primary_author.save()

                # Delete the clone.
                duplicate.delete()
                total_deleted += 1
                
            total_merged += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully merged {total_merged} unique names.\n"
            f"Deleted {total_deleted} duplicate author records."
        ))