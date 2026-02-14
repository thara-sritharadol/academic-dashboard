# ตัวอย่าง code สำหรับโหลดกลับเข้า DB
import json
from api.models import Paper

with open('openalex_concepts_dump.json', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    try:
        paper = Paper.objects.get(id=item['paper_id'])
        paper.openalex_concepts = item['openalex_concepts']
        paper.save()
        print(f"Updated Paper {paper.id}")
    except Paper.DoesNotExist:
        continue