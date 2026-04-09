import json
from django.core.management.base import BaseCommand
from api.models import Paper

"""
For Testing Dataset
"""
class Command(BaseCommand):
    help = "Export papers to a JSON file for Google Colab processing"

    def add_arguments(self, parser):
        parser.add_argument("--output", type=str, default="papers_export.json", help="Output JSON file name")

    def handle(self, *args, **options):
        output_file = options.get("output")
        self.stdout.write(self.style.NOTICE("Fetching papers from Database..."))
        
        # Only paper With abstract, and include 'openalex_concepts' for threshold tuning
        papers = list(
            Paper.objects
            .exclude(abstract__isnull=True)
            .exclude(abstract="")
            .values('id', 'title', 'abstract', 'openalex_concepts')
        )
        
        if not papers:
            self.stdout.write(self.style.ERROR("No papers with abstracts found."))
            return

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=4)

        self.stdout.write(self.style.SUCCESS(f"Successfully exported {len(papers)} papers to {output_file}!"))