import json
import random
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = "Generate datasets with Multi-label concepts and adjustable threshold."

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=float, default=0.3, help='Minimum score for a concept to be included as multi-label')

    def handle(self, *args, **options):
        threshold = options.get('threshold')
        
        papers = Paper.objects.exclude(openalex_concepts__isnull=True).exclude(openalex_concepts__exact=[])
        
        dataset = []

        #ฟังก์ชันหา Concept ที่ได้คะแนนสูงสุดตัวเดียว (สำหรับ NMI / Purity)
        def get_top_concept(concepts, level):
            level_concepts = [c for c in concepts if c.get('level') == level]
            if not level_concepts:
                return None
            level_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            return level_concepts[0]['name']

        #ฟังก์ชันใหม่: ดึงทุก Concept ที่คะแนนผ่านเกณฑ์ (สำหรับ F1-Score)
        def get_multi_labels(concepts, level, thresh):
            return [c['name'] for c in concepts if c.get('level') == level and c.get('score', 0) >= thresh]

        self.stdout.write(f"Filtering papers... (Using Threshold >= {threshold} for multi-labels)")

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
                'id': paper.id,
                'title': title_str,
                'abstract': abstract_str,
                'text': combined_text,
                'doi': paper.doi,
                'true_label_l0': top_l0, # For Hard Clustering
                'true_label_l1': top_l1, # For Hard Clustering
                'multi_labels_l0': multi_l0, # For Multi-label Evaluation
                'multi_labels_l1': multi_l1, # For Multi-label Evaluation
                'multi_labels_l2': multi_l2, # For Multi-label Evaluation
                'openalex_concepts': concepts        # Raw
            }

            allowed_labels = {"Medicine", "Biology"}
            paper_labels = set(multi_l0)

            # เช็คว่ามีข้อมูลใน paper_labels และทุก Label ต้องอยู่ใน allowed_labels เท่านั้น
            if paper_labels and paper_labels.issubset(allowed_labels):
                dataset.append(paper_data)

        self.save_json('dataset_med_bio.json', dataset)


        self.stdout.write(self.style.SUCCESS(
            f"\nDone!\n"
            f"- Dataset: {len(dataset)} papers\n"
        ))

    def save_json(self, filename, data):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)