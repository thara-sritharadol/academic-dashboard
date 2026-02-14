from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.lda_service import LDAService
from sklearn.metrics import normalized_mutual_info_score
from collections import Counter
import numpy as np

class Command(BaseCommand):
    help = 'Run LDA Benchmark with ALL Metrics (Fair Comparison with BERTopic/NMF)'

    def handle(self, *args, **options):
        # --- 1. เตรียมข้อมูล ---
        papers = Paper.objects.exclude(cluster_id__isnull=True)\
                              .exclude(cluster_id=-1)\
                              .exclude(openalex_concepts__isnull=True)\
                              .exclude(abstract__isnull=True)

        if not papers.exists():
            self.stdout.write(self.style.WARNING("No suitable papers found."))
            return

        bertopic_clusters = set(papers.values_list('cluster_id', flat=True))
        n_topics = len(bertopic_clusters)
        
        print(f"Found {papers.count()} papers. Benchmarking LDA with {n_topics} topics.")

        documents = []
        papers_data = [] # เก็บข้อมูลเพื่อใช้คำนวณ F1 (Multi-label)
        y_true_dominant = [] # เก็บเฉลยใบเดียวเพื่อคำนวณ NMI/Purity
        
        for paper in papers:
            text = f"{paper.title} {paper.abstract}"
            concepts = paper.openalex_concepts
            
            # กรอง Concepts สำหรับ Multi-label (Ground Truth Set)
            true_labels_set = set()
            valid_concepts_list = []
            
            for c in concepts:
                 if c.get('level') == 1 and c.get('score', 0) > 0.3:
                     true_labels_set.add(c['name'])
                     valid_concepts_list.append(c)

            if true_labels_set and text.strip():
                # หา Dominant Label (ตัวที่มี Score สูงสุด) สำหรับ NMI/Purity
                valid_concepts_list.sort(key=lambda x: x.get('score', 0), reverse=True)
                top_label = valid_concepts_list[0]['name']

                documents.append(text)
                y_true_dominant.append(top_label)
                
                papers_data.append({
                    "true_labels": true_labels_set,
                    "top_label": top_label
                })

        # --- 2. Run LDA Service ---
        # (LDA Output เป็น Probability Distribution อยู่แล้ว Sum=1)
        lda_service = LDAService(n_topics=n_topics)
        doc_topic_matrix = lda_service.fit_transform(documents)

        # --- 3. คำนวณ NMI & Purity (Hard Clustering Phase) ---
        print("\nCalculating Hard Clustering Metrics (NMI & Purity)...")
        
        # แปลงเป็น Hard Cluster ID (argmax)
        y_pred_hard_ids = np.argmax(doc_topic_matrix, axis=1)
        
        # [A] NMI Score
        nmi = normalized_mutual_info_score(y_true_dominant, y_pred_hard_ids)
        
        # [B] สร้าง Map (Cluster ID -> Label) จาก Majority Vote
        cluster_to_label_map = {}
        for cid in range(n_topics):
            indices = [i for i, x in enumerate(y_pred_hard_ids) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices]
                most_common = Counter(labels_in_cluster).most_common(1)[0][0]
                cluster_to_label_map[cid] = most_common
            else:
                cluster_to_label_map[cid] = "Unknown"

        # [C] Purity Calculation
        y_pred_mapped = [cluster_to_label_map.get(cid, "Unknown") for cid in y_pred_hard_ids]
        correct_count = sum(1 for yt, yp in zip(y_true_dominant, y_pred_mapped) if yt == yp)
        purity = correct_count / len(y_true_dominant)

        # --- 4. คำนวณ Sample-averaged F1 (Multi-label Phase) ---
        print("Calculating Multi-label F1 Score (Sample-averaged)...")
        
        f1_scores = []
        precision_scores = []
        recall_scores = []

        for i, paper_item in enumerate(papers_data):
            true_labels = paper_item["true_labels"]
            pred_labels = set()
            probs = doc_topic_matrix[i]
            
            # Logic: ถ้า Prob > 0.1 ให้ถือว่ามี Topic นั้น (Threshold เดียวกับ BERTopic/NMF)
            for t_id, prob in enumerate(probs):
                if prob > 0.1: 
                    mapped_label = cluster_to_label_map.get(t_id, "Unknown")
                    if mapped_label != "Unknown":
                        pred_labels.add(mapped_label)
            
            # Fallback: ถ้าว่างเปล่า ให้เอาตัว Max
            if not pred_labels:
                max_tid = np.argmax(probs)
                mapped_label = cluster_to_label_map.get(max_tid, "Unknown")
                pred_labels.add(mapped_label)

            # คำนวณ F1 รายใบ
            intersection = len(true_labels & pred_labels)
            p = intersection / len(pred_labels) if len(pred_labels) > 0 else 0
            r = intersection / len(true_labels) if len(true_labels) > 0 else 0
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

            precision_scores.append(p)
            recall_scores.append(r)
            f1_scores.append(f1)

        avg_f1 = np.mean(f1_scores)
        avg_p = np.mean(precision_scores)
        avg_r = np.mean(recall_scores)

        # --- 5. คำนวณ Quality Metrics ---
        diversity = lda_service.calculate_topic_diversity()
        coherence = lda_service.calculate_coherence_score(documents)

        # --- 6. แสดงผลรวม ---
        print("\n" + "="*60)
        print("📊 LDA BENCHMARK RESULTS (Fair Comparison)")
        print("="*60)
        print(f"{'Metric':<30} | {'Score':<10}")
        print("-" * 45)
        # กลุ่ม Hard Clustering
        print(f"{'NMI Score':<30} | {nmi:.4f}")
        print(f"{'Purity':<30} | {purity:.4f}")
        print("-" * 45)
        # กลุ่ม Multi-label
        print(f"{'Sample-avg Precision':<30} | {avg_p:.4f}")
        print(f"{'Sample-avg Recall':<30} | {avg_r:.4f}")
        print(f"{'Sample-avg F1 Score':<30} | {avg_f1:.4f}") 
        print("-" * 45)
        # กลุ่ม Topic Quality
        print(f"{'Topic Diversity':<30} | {diversity:.4f}")
        print(f"{'Topic Coherence (Cv)':<30} | {coherence:.4f}")
        print("="*60)

        # แสดง Mapping
        print("\n🧐 LDA TOPIC MAPPING (First 10 Topics)")
        print("-" * 60)
        topics_words_list = lda_service.get_top_words_list(n_top_words=5)
        
        for cid in range(min(10, n_topics)):
            label = cluster_to_label_map.get(cid, "Unknown")
            words = ", ".join(topics_words_list[cid]) if cid < len(topics_words_list) else ""
            print(f"Topic {cid:<2} -> {label:<25} | Keywords: {words}")