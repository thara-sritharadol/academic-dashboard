from django.core.management.base import BaseCommand
from api.services.skill_embedding_builder import build_and_save_skill_embeddings

class Command(BaseCommand):
    help = "Build skill embeddings from a CSV file and save them to the database"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the skills dataset (CSV)")
        parser.add_argument(
            "--model", 
            type=str, 
            default="all-mpnet-base-v2", 
            help="Name of the SentenceTransformer model to use"
        )
        parser.add_argument(
            "--limit", 
            type=int, 
            help="Limit the number of skills to process"
        )
        parser.add_argument(
            "--source",
            type=str,
            default="MANUAL",
            help="Source of the skills (e.g., MANUAL, ACM_CCS)"
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        model_name = options["model"]
        limit = options.get("limit")
        source = options.get("source")

        self.stdout.write(self.style.NOTICE(f"Starting to build skill embeddings from {csv_path}"))
        
        num_records = build_and_save_skill_embeddings(
            csv_path, 
            model_name=model_name, 
            source=source,
            limit=limit
        )
        
        self.stdout.write(self.style.SUCCESS(f"Done! Saved {num_records:,} skill embeddings to the database."))