import json
import random
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = "Generate datasets with Multi-label and Single-label concepts."

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=float, default=0.3, help='Minimum score for a concept')
        parser.add_argument('--target_labels', nargs='+', default=['Mathematics', 'Computer science'], help='List of target Level 0 labels')
        
        # --- ปรับค่าเริ่มต้น min_match เป็น 1 และเพิ่มเงื่อนไขใหม่ ---
        parser.add_argument('--min_match', type=int, default=1, help='Minimum number of target labels (1 for single+multi, 2 for multi only)')
        parser.add_argument('--max_match', type=int, default=None, help='Maximum number of target labels (e.g., 1 for strictly single label)')
        parser.add_argument('--strict_domain', action='store_true', help='If set, the paper must NOT contain any labels outside the target_labels')
        
        parser.add_argument('--output', type=str, default='dataset_mixed_labels.json', help='Output JSON filename')

    def handle(self, *args, **options):
        threshold = options.get('threshold')
        target_labels = set(options.get('target_labels'))
        min_match = options.get('min_match')
        max_match = options.get('max_match')
        strict_domain = options.get('strict_domain')
        output_file = options.get('output')
        
        papers = Paper.objects.exclude(openalex_concepts__isnull=True).exclude(openalex_concepts__exact=[])
        
        dataset = []

        # ฟังก์ชันหา Concept ที่ได้คะแนนสูงสุดตัวเดียว
        def get_top_concept(concepts, level):
            level_concepts = [c for c in concepts if c.get('level') == level]
            if not level_concepts:
                return None
            level_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            return level_concepts[0]['name']

        # ฟังก์ชันดึงทุก Concept ที่คะแนนผ่านเกณฑ์
        def get_multi_labels(concepts, level, thresh):
            return [c['name'] for c in concepts if c.get('level') == level and c.get('score', 0) >= thresh]

        self.stdout.write(f"Filtering papers... (Threshold >= {threshold})")
        self.stdout.write(f"Condition: Matches between {min_match} and {max_match if max_match else 'Any'} labels from {list(target_labels)}")
        if strict_domain:
            self.stdout.write("Strict Domain: ON (No outside labels allowed)")

        for paper in papers:
            concepts = paper.openalex_concepts
            if not isinstance(concepts, list):
                continue
                
            top_l0 = get_top_concept(concepts, 0)
            top_l1 = get_top_concept(concepts, 1)
            
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

            # 1. เช็คจำนวนที่ Match กับ Target ที่ต้องการ
            match_count = len(paper_labels.intersection(target_labels))
            
            # 2. เช็คเงื่อนไข Strict Domain (ถ้าเปิดไว้ ห้ามมี Label อื่นที่ไม่ใช่ Target ปะปนมา)
            is_strict_pass = True
            if strict_domain:
                is_strict_pass = paper_labels.issubset(target_labels)

            # 3. ตรวจสอบเงื่อนไขทั้งหมดก่อนบันทึกลง Dataset
            if match_count >= min_match and is_strict_pass:
                if max_match is None or match_count <= max_match:
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