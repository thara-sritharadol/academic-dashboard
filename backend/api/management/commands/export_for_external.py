#For Developing
import json
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = "Export abstracts for processing on Google Colab"

    def handle(self, *args, **options):
        #ดึงเฉพาะ Paper ที่มี Abstract
        papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract='')
        
        data = []
        print(f"Exporting {papers.count()} papers...")
        
        for p in papers:
            data.append({
                "id": p.id,
                "abstract": p.abstract
            })

        # 2. บันทึกเป็นไฟล์ JSON
        filename = "papers_export.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Successfully exported to '{filename}'"))