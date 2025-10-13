from django.core.management.base import BaseCommand
from api.services.skill_clustering_from_db import cluster_skills_from_db

class Command(BaseCommand):
    help = "Cluster skills already stored in SkillEmbedding table (merge synonyms and export CSV)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            default="all-mpnet-base-v2",
            help="Name of the SentenceTransformer model used for skill embeddings."
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.85,
            help="Cosine similarity threshold for merging (0.8–0.9 typical)."
        )
        parser.add_argument(
            "--no-save",
            action="store_true",
            help="Do not save CSV output files, only show summary in console."
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        threshold = options["threshold"]
        save_csv = not options["no_save"]

        self.stdout.write(self.style.NOTICE(
            f"🚀 เริ่ม clustering skills จาก DB (model={model_name}, threshold={threshold})"
        ))
        df, df_rep = cluster_skills_from_db(
            model_name=model_name,
            threshold=threshold,
            save_csv=save_csv
        )

        if df_rep is not None:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Clustering เสร็จสิ้น ได้ทั้งหมด {len(df_rep):,} กลุ่ม representative skills"
            ))
        else:
            self.stdout.write(self.style.ERROR("❌ ไม่สามารถสร้าง cluster ได้"))
