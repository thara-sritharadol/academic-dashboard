import json
import random
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = "Generate datasets with Multi-label concepts and adjustable threshold."

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=float, default=0.3, help='Minimum score for a concept to be included as multi-label')
        # เพิ่ม Arguments ใหม่เพื่อให้รับค่า Label ที่ต้องการและจำนวนขั้นต่ำได้ผ่าน Command line
        parser.add_argument('--target_labels', nargs='+', default=['Mathematics', 'Computer science'], help='List of target Level 0 labels (e.g., "Mathematics" "Computer science")')
        parser.add_argument('--min_match', type=int, default=2, help='Minimum number of target labels the paper must contain')
        parser.add_argument('--output', type=str, default='dataset_multi_label_strict.json', help='Output JSON filename')

    def handle(self, *args, **options):
        threshold = options.get('threshold')
        target_labels = set(options.get('target_labels'))
        min_match = options.get('min_match')
        output_file = options.get('output')
        
        papers = Paper.objects.exclude(openalex_concepts__isnull=True).exclude(openalex_concepts__exact=[])
        
        dataset = []

        # ฟังก์ชันหา Concept ที่ได้คะแนนสูงสุดตัวเดียว (สำหรับ NMI / Purity)
        def get_top_concept(concepts, level):
            level_concepts = [c for c in concepts if c.get('level') == level]
            if not level_concepts:
                return None
            level_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            return level_concepts[0]['name']

        # ฟังก์ชันดึงทุก Concept ที่คะแนนผ่านเกณฑ์ (สำหรับ F1-Score)
        def get_multi_labels(concepts, level, thresh):
            return [c['name'] for c in concepts if c.get('level') == level and c.get('score', 0) >= thresh]

        self.stdout.write(f"Filtering papers... (Threshold >= {threshold})")
        self.stdout.write(f"Condition: Must contain at least {min_match} labels from {list(target_labels)}")

        for paper in papers:
            concepts = paper.openalex_concepts
            if not isinstance(concepts, list):
                continue
                
            # --- ดึง Top Label ---
            top_l0 = get_top_concept(concepts, 0)
            top_l1 = get_top_concept(concepts, 1)
            
            # --- ดึง Multi-labels ---
            multi_l0 = get_multi_labels(concepts, 0, threshold)
            multi_l1 = get_multi_labels(concepts, 1, threshold)
            multi_l2 = get_multi_labels(concepts, 2, threshold)
            
            title_str = paper.title if paper.title else ""
            abstract_str = paper.abstract if hasattr(paper, 'abstract') and paper.abstract else ""
            combined_text = f"{title_str}. {abstract_str}".strip()

            if not combined_text or combined_text == ".":
                continue

            paper_data = {
                'id': str(paper.id),
                'title': title_str,
                'abstract': abstract_str,
                'text': combined_text,
                'doi': paper.doi,
                'true_label_l0': top_l0, 
                'true_label_l1': top_l1, 
                'multi_labels_l0': multi_l0, 
                'multi_labels_l1': multi_l1, 
                'multi_labels_l2': multi_l2, 
                'openalex_concepts': concepts 
            }

            paper_labels = set(multi_l0)

            # --- จุดที่เปลี่ยนแปลง ---
            # ใช้ intersection เพื่อหาจุดตัดระหว่าง Label ของ Paper กับ Target ที่เราต้องการ
            # ถ้ามีจุดตัด >= min_match แสดงว่าตรงตามเงื่อนไข (และอนุญาตให้มี Label อื่นที่ไม่อยู่ใน Target ติดมาด้วยได้)
            if len(paper_labels.intersection(target_labels)) >= min_match:
                dataset.append(paper_data)

        self.save_json(output_file, dataset)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone!\n"
            f"- Dataset saved to: {output_file}\n"
            f"- Total papers matching criteria: {len(dataset)} papers\n"
        ))

    def save_json(self, filename, data):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)