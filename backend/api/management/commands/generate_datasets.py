import json
import random
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = "Generate 3 datasets (Easy, Medium, Hard) with Multi-label concepts and adjustable threshold."

    def add_arguments(self, parser):
        # เพิ่ม Option ให้กำหนดค่า Threshold ได้ผ่าน Command Line (ค่า Default คือ 0.3)
        parser.add_argument('--threshold', type=float, default=0.3, help='Minimum score for a concept to be included as multi-label')

    def handle(self, *args, **options):
        threshold = options.get('threshold')
        
        papers = Paper.objects.exclude(openalex_concepts__isnull=True).exclude(openalex_concepts__exact=[])
        
        dataset_easy = []
        dataset_medium = []
        dataset_hard = []

        # 1. ฟังก์ชันหา Concept ที่ได้คะแนนสูงสุดตัวเดียว (สำหรับ NMI / Purity)
        def get_top_concept(concepts, level):
            level_concepts = [c for c in concepts if c.get('level') == level]
            if not level_concepts:
                return None
            level_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            return level_concepts[0]['name']

        # 2. ฟังก์ชันใหม่: ดึงทุก Concept ที่คะแนนผ่านเกณฑ์ (สำหรับ F1-Score)
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
                'true_label_l0': top_l0,             # สำหรับ Hard Clustering
                'true_label_l1': top_l1,             # สำหรับ Hard Clustering
                'multi_labels_l0': multi_l0,         # สำหรับ Multi-label Evaluation
                'multi_labels_l1': multi_l1,         # สำหรับ Multi-label Evaluation
                'multi_labels_l2': multi_l2,         # สำหรับ Multi-label Evaluation
                'openalex_concepts': concepts        # เก็บ Raw เผื่อต้องใช้อย่างอื่น
            }

            # กรองชุด Easy (แยกโดเมนชัดเจน - Level 0)
            if top_l0 in ["Medicine", "Chemistry"]:
                dataset_easy.append(paper_data)
                
            # กรองชุด Medium (สาขาย่อยใกล้เคียงกัน - Level 1)
            if top_l1 in ["Artificial intelligence", "Statistics", "Machine learning", "Algorithm", "Information retrieval", "Mathematical optimization", "Data mining", "Natural language processing"]:
                dataset_medium.append(paper_data)

        # 3. กรองชุด Hard (Imbalanced Data จากกลุ่ม Medium)
        # แก้ไขเงื่อนไขให้ดึงจาก L1 ที่มีอยู่จริงใน dataset_medium เพื่อไม่ให้ list ว่างเปล่า
        ai_papers = [p for p in dataset_medium if p['true_label_l1'] == "Artificial intelligence"]
        ml_papers = [p for p in dataset_medium if p['true_label_l1'] == "Machine learning"]
        algo_papers = [p for p in dataset_medium if p['true_label_l1'] == "Algorithm"]

        if ai_papers and ml_papers and algo_papers:
            n_ai = min(len(ai_papers), 800)
            n_ml = min(len(ml_papers), int(n_ai * 0.15 / 0.8)) # ประมาณ 15%
            n_algo = min(len(algo_papers), int(n_ai * 0.05 / 0.8)) # ประมาณ 5%
            
            dataset_hard.extend(random.sample(ai_papers, n_ai))
            dataset_hard.extend(random.sample(ml_papers, max(1, n_ml)))
            dataset_hard.extend(random.sample(algo_papers, max(1, n_algo)))
            random.shuffle(dataset_hard)

        # --- บันทึกไฟล์ JSON ---
        self.save_json('dataset_med_chem.json', dataset_easy)
        self.save_json('dataset_medium_overlap.json', dataset_medium)
        self.save_json('dataset_hard_imbalanced.json', dataset_hard)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone!\n"
            f"- Easy Dataset (Distinct): {len(dataset_easy)} papers\n"
            f"- Medium Dataset (Overlap): {len(dataset_medium)} papers\n"
            f"- Hard Dataset (Imbalanced): {len(dataset_hard)} papers"
        ))

    def save_json(self, filename, data):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)