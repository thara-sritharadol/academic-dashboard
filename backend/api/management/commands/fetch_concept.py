import time
import json
import requests
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = 'Fetch concepts from OpenAlex using DOI and save to JSON'

    def handle(self, *args, **options):
        # 1. เตรียมข้อมูล
        papers = Paper.objects.exclude(doi__isnull=True).exclude(doi__exact='')
        results = []
        
        print(f"Found {papers.count()} papers with DOI. Starting fetch...")

        # ใส่ Email เพื่อให้ OpenAlex รู้ว่าเราไม่ใช่ Bot ตัวร้าย (จะได้ Rate Limit ที่ดีขึ้น)
        headers = {
            'User-Agent': 'mailto:your_email@university.ac.th' 
        }

        # 2. วนลูปดึงข้อมูล
        for index, paper in enumerate(papers):
            doi = paper.doi.strip()
            
            # จัด Format DOI ให้ OpenAlex เข้าใจ (ต้องมี https://doi.org/)
            if not doi.startswith('http'):
                doi_url = f"https://doi.org/{doi}"
            else:
                doi_url = doi

            # OpenAlex API Endpoint
            # เราใช้ filter=doi:... เพื่อความแม่นยำ
            api_url = f"https://api.openalex.org/works/{doi_url}"

            try:
                response = requests.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # ดึงเฉพาะ Concepts
                    # OpenAlex ให้มาเยอะมาก เราเอาแค่ที่ Score สูงๆ หรือเอามาหมดแล้วไปกรองทีหลังก็ได้
                    # ในที่นี้ผมดึงมาหมดแต่จัด Format ให้ย่อลง
                    concepts = []
                    for c in data.get('concepts', []):
                        concepts.append({
                            'id': c['id'],
                            'name': c['display_name'],
                            'level': c['level'], # Level 0 = Domain, 1 = Field, 2 = Sub-field
                            'score': c['score']  # ความมั่นใจของ OpenAlex (0-1)
                        })

                    # เตรียมข้อมูลสำหรับบันทึก
                    paper_data = {
                        'paper_id': paper.id,
                        'title': paper.title,
                        'doi': paper.doi,
                        'openalex_concepts': concepts
                    }
                    results.append(paper_data)
                    print(f"[{index+1}/{papers.count()}] Success: {paper.title[:30]}... ({len(concepts)} concepts)")
                
                elif response.status_code == 404:
                    print(f"[{index+1}/{papers.count()}] Not Found in OpenAlex: {doi}")
                else:
                    print(f"[{index+1}/{papers.count()}] Error {response.status_code}: {doi}")

            except Exception as e:
                print(f"Error fetching {doi}: {str(e)}")

            # Sleep นิดหน่อยเพื่อความสุภาพ (OpenAlex ให้ 100k req/day แต่กันเหนียว)
            time.sleep(0.1)

        # 3. บันทึกลงไฟล์ JSON
        output_file = 'openalex_concepts_dump.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        print(f"\nFinished! Saved data to {output_file}")