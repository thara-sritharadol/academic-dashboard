import json
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Paper #

class Command(BaseCommand):
    help = "Import BERTopic clustering results from Google Colab"

    def add_arguments(self, parser):
        parser.add_argument("--input", type=str, default="bertopic_results.json", help="Input JSON result file")

    def handle(self, *args, **options):
        input_file = options.get("input")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File {input_file} not found."))
            return

        self.stdout.write(self.style.NOTICE(f"Updating {len(results)} papers in Database..."))
        
        updated_count = 0
        
        # ใช้ transaction.atomic() เพื่อให้ Database ทำงานเร็วขึ้นตอน Update รวดเดียว
        with transaction.atomic():
            for result in results:
                Paper.objects.filter(id=result['id']).update(
                    cluster_id=result['cluster_id'],
                    cluster_label=result['cluster_label'],
                    predicted_multi_labels=result['predicted_multi_labels'],
                    topic_keywords=result['topic_keywords']
                    # topic_distribution=result.get('topic_distribution') # ถ้าเก็บ distribution มาด้วย
                )
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} papers!"))