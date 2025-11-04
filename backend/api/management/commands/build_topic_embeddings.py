from django.core.management.base import BaseCommand
from api.services.topic_embedding_builder import build_and_save_topic_embeddings

class Command(BaseCommand):
    help = "Build topic embeddings from a CSV file and save them to the database"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the topics dataset (CSV)")
        parser.add_argument(
            "--model", 
            type=str, 
            default="allenai/specter2_base", 
            help="Name of the SentenceTransformer model to use"
        )
        parser.add_argument(
            "--limit", 
            type=int, 
            help="Limit the number of topics to process"
        )
        parser.add_argument(
            "--source",
            type=str,
            default="MANUAL",
            help="Source of the topics (e.g., MANUAL, ACM_CCS)"
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        model_name = options["model"]
        limit = options.get("limit")
        source = options.get("source")

        self.stdout.write(self.style.NOTICE(f"🚀 Starting to build topic embeddings from {csv_path}"))
        
        num_records = build_and_save_topic_embeddings(
            csv_path, 
            model_name=model_name, 
            source=source,
            limit=limit
        )
        
        self.stdout.write(self.style.SUCCESS(f"✅ Done! Saved {num_records:,} topic embeddings to the database."))