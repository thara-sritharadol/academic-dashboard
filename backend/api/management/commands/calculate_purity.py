from collections import Counter
from django.core.management.base import BaseCommand
from api.models import Paper
import numpy as np

class Command(BaseCommand):
    help = 'Calculate Purity Score and Compare BERTopic Representation with OpenAlex'

    def handle(self, *args, **options):
        # 1. ดึงข้อมูล Papers
        # ไม่เอา Outlier (-1)
        papers = Paper.objects.exclude(cluster_id__isnull=True)\
                              .exclude(cluster_id=-1)\
                              .exclude(openalex_concepts__isnull=True)
        
        if not papers.exists():
            self.stdout.write(self.style.WARNING("No papers found with both cluster_id and OpenAlex concepts."))
            return

        print(f"Analyzing {papers.count()} papers...")

        # Data structures
        # { cluster_id: [list_of_openalex_labels] }
        clusters_ground_truth = {}
        # { cluster_id: "topic_words_string" } เพื่อเก็บ Keywords ของกลุ่มนั้น
        cluster_topic_repr = {}
        
        total_valid_papers = 0

        # 2. วนลูปเพื่อ Assign Ground Truth และเก็บ Keywords
        for paper in papers:
            concepts = paper.openalex_concepts
            if not concepts:
                continue

            # กรองเอาเฉพาะ Level 1 หรือ 2 และ Score > 0.3
            valid_concepts = [
                c for c in concepts 
                if c.get('level') in [1] and c.get('score', 0) > 0.3
            ]
            
            # เรียงลำดับเอา Score มากสุดขึ้นก่อน
            valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)

            if not valid_concepts:
                continue

            # เลือก Concept ที่ Score สูงสุดเป็น Label
            top_concept_name = valid_concepts[0]['name']

            c_id = paper.cluster_id
            
            # เก็บ Ground Truth
            if c_id not in clusters_ground_truth:
                clusters_ground_truth[c_id] = []
            clusters_ground_truth[c_id].append(top_concept_name)
            
            # เก็บ Topic Keywords (เก็บแค่ครั้งเดียวต่อ Cluster ก็พอ เพราะเหมือนกันทั้งกลุ่ม)
            if c_id not in cluster_topic_repr and paper.cluster_label:
                cluster_topic_repr[c_id] = paper.cluster_label

            total_valid_papers += 1

        # 3. แสดงผลตารางเปรียบเทียบ
        sum_max_class_counts = 0
        
        # จัด Format ตารางให้กว้างขึ้นเพื่อรองรับ Keywords
        # ID | BERTopic Words | OpenAlex Concept | Purity | Size
        header = f"{'ID':<4} | {'BERTopic Keywords':<40} | {'OpenAlex Concept (Ground Truth)':<35} | {'Purity':<8} | {'Size':<5}"
        divider = "=" * len(header)
        
        print("\n" + divider)
        print(header)
        print(divider)

        results = []

        for c_id, labels in clusters_ground_truth.items():
            # หา Dominant Class (OpenAlex)
            label_counts = Counter(labels)
            most_common_label, count = label_counts.most_common(1)[0]
            
            sum_max_class_counts += count
            local_purity = count / len(labels)
            
            # ดึง Keywords ของ BERTopic มาแสดง
            topic_words = cluster_topic_repr.get(c_id, "N/A")
            # ตัดคำถ้ามันยาวเกินไปเพื่อความสวยงามของตาราง
            if len(topic_words) > 38:
                topic_words = topic_words[:35] + "..."
            
            results.append((c_id, topic_words, most_common_label, local_purity, len(labels)))

        # เรียงตาม ID
        results.sort(key=lambda x: x[0])

        for res in results:
            print(f"{res[0]:<4} | {res[1]:<40} | {res[2]:<35} | {res[3]:.4f}   | {res[4]:<5}")

        print(divider)

        # 4. Final Score
        total_purity = sum_max_class_counts / total_valid_papers if total_valid_papers > 0 else 0
        
        print(f"\n>>> Overall System Purity: {total_purity:.4f}")
        print(f">>> (Calculated on {total_valid_papers} matched papers)")