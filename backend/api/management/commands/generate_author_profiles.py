from django.core.management.base import BaseCommand
from api.pipelines.author_profile_service import AuthorProfileService

class Command(BaseCommand):
    help = "Generate primary cluster and topic profile distributions for all authors based on their papers."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Calculating Author Profiles (Aggregating Topic Distributions)..."))
        
        result = AuthorProfileService.generate_all_profiles()
        
        self.stdout.write(self.style.SUCCESS(f"Done! {result['message']}"))