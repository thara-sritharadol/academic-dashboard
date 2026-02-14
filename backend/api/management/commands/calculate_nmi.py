from django.core.management.base import BaseCommand
from api.models import Paper
from sklearn.metrics import normalized_mutual_info_score
import numpy as np

class Command(BaseCommand):
    help = 'Calculate Normalized Mutual Information (NMI) between BERTopic clusters and OpenAlex Concepts'

    def handle(self, *args, **options):
        # 1. ดึงข้อมูล Papers
        # กรองเอาเฉพาะที่มีทั้ง Cluster ID และ OpenAlex Concepts
        # และไม่เอา Outlier (-1) เพราะ Outlier ไม่ใช่กลุ่มที่แท้จริง
        papers = Paper.objects.exclude(cluster_id__isnull=True)\
                              .exclude(cluster_id=-1)\
                              .exclude(openalex_concepts__isnull=True)

        if not papers.exists():
            self.stdout.write(self.style.WARNING("No matched papers found."))
            return

        print(f"Calculating NMI on {papers.count()} papers...")

        y_true = [] # เฉลยจาก OpenAlex
        y_pred = [] # ผลลัพธ์จาก BERTopic

        # 2. เตรียมข้อมูลสำหรับ Sklearn
        for paper in papers:
            concepts = paper.openalex_concepts
            if not concepts:
                continue

            # ใช้ Logic เดิม: เอา Concept Level 1 ที่ Score สูงสุดมาเป็นเฉลย
            valid_concepts = [
                c for c in concepts 
                if c.get('level') == 1 and c.get('score', 0) > 0.3 
            ]
            
            if not valid_concepts:
                continue
            
            # เรียงลำดับและเลือกตัวแรก
            valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            top_concept_name = valid_concepts[0]['name']

            # เก็บลง List
            y_true.append(top_concept_name)
            y_pred.append(paper.cluster_id)

        # 3. คำนวณ NMI
        # average_method='geometric' เป็นค่า default มาตรฐาน
        nmi_score = normalized_mutual_info_score(y_true, y_pred)

        print("-" * 40)
        print(f"Total Papers Used: {len(y_true)}")
        print(f"NMI Score:         {nmi_score:.4f}")
        print("-" * 40)
        
        # 4. แปลผลเบื้องต้นให้
        if nmi_score > 0.5:
            print("Interpretaion: Excellent match! The clusters align very well with OpenAlex concepts.")
        elif nmi_score > 0.3:
            print("Interpretaion: Good match. There is a strong correlation.")
        else:
            print("Interpretaion: Low match. The clustering structure differs significantly from OpenAlex.")