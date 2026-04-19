from django.core.management.base import BaseCommand
from api.pipelines.tu_sync_service import TUSyncService

class Command(BaseCommand):
    help = "Fetch all faculties and authors from TU API and save to the local database"

    def add_arguments(self, parser):
        parser.add_argument("--api_key", type=str, required=True, help="TU API Access Token")
        parser.add_argument("--faculty", type=str, help="Specific Faculty_Name_En to fetch")

    def handle(self, *args, **options):
        api_key = options.get("api_key")
        specific_faculty = options.get("faculty")

        self.stdout.write(self.style.NOTICE("Starting sync via Service..."))
        
        service = TUSyncService(api_key=api_key)
        result = service.sync_authors(specific_faculty=specific_faculty)

        if result.get("status") == "success":
            self.stdout.write(self.style.SUCCESS(
                f"\nSync Complete!\n"
                f"   - New Authors Added: {result['saved']}\n"
                f"   - Existing Authors Updated: {result['updated']}"
            ))
        else:
            self.stdout.write(self.style.ERROR(result.get("message")))