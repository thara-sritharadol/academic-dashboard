from collections import Counter
from django.core.management.base import BaseCommand
from api.models import Paper
import numpy as np

class Command(BaseCommand):
    help = 'Calculate Sample-averaged F1 Score and Show Topic Keywords Mapping'

    def handle(self, *args, **options):
        # 1. เตรียมข้อมูล
        papers = Paper.objects.exclude(cluster_id__isnull=True)\
                              .exclude(cluster_id=-1)\
                              .exclude(openalex_concepts__isnull=True)
        
        if not papers.exists():
            self.stdout.write(self.style.WARNING("No matched papers found."))
            return

        print(f"1. Building Topic-to-Label Map (using {papers.count()} papers)...")

        # --- Phase 1: สร้าง Map ว่า Cluster ไหน แปลว่าอะไร (Mapping) ---
        cluster_votes = {}    # { cluster_id: [list of labels] }
        cluster_keywords = {} # { cluster_id: "keywords string" }

        for paper in papers:
            # ดึงเฉลยใบหลัก (Dominant Label) จาก OpenAlex
            concepts = paper.openalex_concepts
            valid_concepts = [c for c in concepts if c.get('level') == 1 and c.get('score', 0) > 0.3]
            valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            if not valid_concepts: continue
            top_label = valid_concepts[0]['name']

            c_id = paper.cluster_id
            
            # เก็บ Vote
            if c_id not in cluster_votes: 
                cluster_votes[c_id] = []
            cluster_votes[c_id].append(top_label)

            # เก็บ Keywords (ถ้ายังไม่มีใน Dict)
            # เราดึงจาก paper.cluster_label ที่บันทึกไว้ตอนทำ Clustering
            if c_id not in cluster_keywords and paper.cluster_label:
                cluster_keywords[c_id] = paper.cluster_label

        # สรุปผลโหวตและแสดงตาราง
        topic_map = {}
        
        # จัด Format หัวตาราง
        header = f"{'ID':<4} | {'BERTopic Keywords':<40} | {'Mapped Label (Majority Vote)':<30}"
        divider = "-" * len(header)

        print("\n" + divider)
        print(header)
        print(divider)
        
        # เรียงตาม ID เพื่อความสวยงาม
        sorted_ids = sorted(cluster_votes.keys())

        for c_id in sorted_ids:
            votes = cluster_votes[c_id]
            majority_label = Counter(votes).most_common(1)[0][0]
            topic_map[c_id] = majority_label
            
            # ดึง Keywords มาแสดง
            keywords = cluster_keywords.get(c_id, "N/A")
            if len(keywords) > 38: # ตัดคำถ้ายาวเกิน
                keywords = keywords[:35] + "..."

            print(f"{c_id:<4} | {keywords:<40} | {majority_label:<30}")

        print(divider)

        # --- Phase 2: คำนวณ F1-Score รายใบ (Multi-label Evaluation) ---
        print("\n2. Calculating Multi-label F1 Score per paper...")
        
        f1_scores = []
        precision_scores = []
        recall_scores = []

        for paper in papers:
            # A. หา Set ของ "เฉลย" (True Labels)
            true_labels = set()
            for c in paper.openalex_concepts:
                if c.get('level') == 1 and c.get('score', 0) > 0.3:
                    true_labels.add(c['name'])
            
            if not true_labels: continue

            # B. หา Set ของ "คำทำนาย" (Predicted Labels)
            pred_labels = set()
            dist = paper.topic_distribution # list of {topic_id, prob, ...}
            
            if dist:
                for item in dist:
                    t_id = item.get('topic_id')
                    prob = item.get('prob', 0)
                    
                    # Threshold: ถ้า prob เกิน 0.1 ถือว่าโมเดล "ทาย" หัวข้อนี้
                    if prob > 0.1 and t_id in topic_map:
                        mapped_label = topic_map[t_id]
                        pred_labels.add(mapped_label)
            
            # Fallback: ถ้า Distribution ว่าง ให้ใช้ Hard Cluster
            if not pred_labels and paper.cluster_id in topic_map:
                 pred_labels.add(topic_map[paper.cluster_id])

            # C. คำนวณ F1
            intersection = len(true_labels & pred_labels)
            
            p = intersection / len(pred_labels) if len(pred_labels) > 0 else 0
            r = intersection / len(true_labels) if len(true_labels) > 0 else 0
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

            precision_scores.append(p)
            recall_scores.append(r)
            f1_scores.append(f1)

        # --- สรุปผล ---
        avg_f1 = np.mean(f1_scores)
        avg_p = np.mean(precision_scores)
        avg_r = np.mean(recall_scores)

        print("=" * 60)
        print("MULTI-LABEL PERFORMANCE METRICS")
        print("=" * 60)
        print(f"Sample-averaged Precision: {avg_p:.4f}")
        print(f"Sample-averaged Recall:    {avg_r:.4f}")
        print(f"Sample-averaged F1-Score:  {avg_f1:.4f}")
        print("=" * 60)
        
        if avg_f1 > 0.4:
            print("Interpretation: Good multi-label capability for unsupervised model.")
        else:
            print("Interpretation: Moderate. The model relies heavily on the dominant topic.")