from django.core.management.base import BaseCommand
from api.pipelines.data_deduplication_service import DataDeduplicationService

class Command(BaseCommand):
    help = "Merge duplicate authors based on exact case-insensitive name matching"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Scanning for duplicate authors..."))
        result = DataDeduplicationService.merge_duplicate_authors()
        
        if result["deleted"] == 0:
            self.stdout.write(self.style.SUCCESS(result["message"]))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccess! {result['message']}"))