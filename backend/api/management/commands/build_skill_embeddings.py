from django.core.management.base import BaseCommand
from api.services.skill_embedding_builder import build_and_save_skill_embeddings_from_description

class Command(BaseCommand):
    help = "Build and deduplicate skill embeddings from CSV and save to database"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to skill dataset (CSV)")
        parser.add_argument("--model", type=str, default="allenai/specter2")
        parser.add_argument("--limit", type=int)
        #parser.add_argument("--threshold", type=float, default=1, help="Cosine similarity threshold for merging")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        model_name = options["model"]
        limit = options.get("limit")
        #threshold = options["threshold"]

        self.stdout.write(self.style.NOTICE(f"เริ่มสร้าง embeddings จาก {csv_path}"))
        #n = build_and_save_skill_embeddings_dedup(csv_path, model_name=model_name, limit=limit, similarity_threshold=threshold)
        n = build_and_save_skill_embeddings_from_description(csv_path, model_name=model_name, limit=limit)
        self.stdout.write(self.style.SUCCESS(f"🎯 เสร็จสิ้น! บันทึก skill {n:,} รายการลงฐานข้อมูล"))
