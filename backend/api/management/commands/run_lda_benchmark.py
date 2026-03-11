import csv
import json
import time
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.lda_service import LDAService
from sklearn.metrics import normalized_mutual_info_score
from collections import Counter
import numpy as np

class Command(BaseCommand):
    help = 'Run LDA Benchmark with Time Tracking, Metrics Export, and pyLDAvis HTML'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, help='Path to JSON dataset (optional)')
        parser.add_argument('--k', type=int, help='Manually set number of topics K (optional)')
        parser.add_argument('--threshold', type=float, default=0.3, help='Score threshold for multi-labels')
        parser.add_argument('--target_level', type=int, choices=[0, 1, 2], default=1, help='Target concept level')
        parser.add_argument('--export_json', type=str, help='File path to export results as JSON')
        parser.add_argument('--export_csv', type=str, help='File path to export results as CSV')
        parser.add_argument('--export_html', type=str, help='File path to export pyLDAvis HTML (e.g., lda_vis.html)')
        parser.add_argument('--export_barchart', type=str, help='File path to export Top Words Bar Chart (e.g., lda_bar.png)')
        parser.add_argument('--export_scatter', type=str, help='File path to export UMAP Scatter Plot (e.g., lda_scatter.png)')
        parser.add_argument('--export_scatter_3d', type=str, help='File path to export UMAP 3D Scatter Plot HTML (e.g., lda_scatter_3d.html)')

    def handle(self, *args, **options):
        input_file = options.get('input')
        k_option = options.get('k')
        threshold = options.get('threshold')
        target_level = options.get('target_level')
        export_json = options.get('export_json')
        export_csv = options.get('export_csv')
        export_html = options.get('export_html')
        export_barchart = options.get('export_barchart')
        export_scatter = options.get('export_scatter')
        export_scatter_3d = options.get('export_scatter_3d')
        
        documents = []
        papers_data = [] 
        y_true_dominant = [] 

        target_key_hard = f'true_label_l{target_level}'
        target_key_multi = f'multi_labels_l{target_level}'

        # --- เตรียมข้อมูลสำหรับการทดสอบ ---
        if input_file:
            self.stdout.write(self.style.NOTICE(f"Loading data from JSON: {input_file}"))
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                text = item.get('text', '')
                if not text:
                    text = f"{item.get('title', '')} {item.get('abstract', '')}"

                true_labels_set = set()
                top_label = item.get(target_key_hard)

                if target_key_multi in item and isinstance(item[target_key_multi], list):
                    true_labels_set = set(item[target_key_multi])
                elif 'openalex_concepts' in item:
                    valid_concepts = []
                    for c in item['openalex_concepts']:
                         if c.get('level') == target_level and c.get('score', 0) >= threshold:
                             true_labels_set.add(c['name'])
                             valid_concepts.append(c)
                    if valid_concepts and not top_label:
                        valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                        top_label = valid_concepts[0]['name']
                else:
                    if top_label:
                        true_labels_set.add(top_label)

                if true_labels_set and top_label and text.strip():
                    documents.append(text) 
                    y_true_dominant.append(top_label)
                    
                    papers_data.append({
                        "id": str(item.get('id', 'N/A')),
                        "title": str(item.get('title', 'Unknown Title')).replace('\n', ' ').replace('\r', ''),
                        "true_labels": list(true_labels_set), 
                        "top_label": str(top_label)
                    })
            n_topics = k_option if k_option else len(set(y_true_dominant))
        else:
            self.stdout.write(self.style.NOTICE(f"Loading data from DB..."))
            papers = Paper.objects.exclude(cluster_id__isnull=True).exclude(cluster_id=-1).exclude(openalex_concepts__isnull=True).exclude(abstract__isnull=True)
            if not papers.exists(): return
            for paper in papers:
                text = f"{paper.title} {paper.abstract}"
                concepts = paper.openalex_concepts
                true_labels_set = set()
                valid_concepts = []
                for c in concepts:
                     if c.get('level') == target_level and c.get('score', 0) >= threshold:
                         true_labels_set.add(c['name'])
                         valid_concepts.append(c)
                if true_labels_set and text.strip():
                    valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                    top_label = valid_concepts[0]['name']
                    documents.append(text)
                    y_true_dominant.append(top_label)
                    papers_data.append({
                        "id": str(paper.id),
                        "title": str(paper.title).replace('\n', ' ').replace('\r', ''),
                        "true_labels": list(true_labels_set),
                        "top_label": str(top_label)
                    })
            n_topics = k_option if k_option else len(set(papers.values_list('cluster_id', flat=True)))

        if not documents: return
        print(f"Found {len(documents)} papers. Benchmarking LDA with {n_topics} topics.")

        # --- 2. Run LDA Service (พร้อมจับเวลา) ---
        start_time = time.time()
        lda_service = LDAService(n_topics=n_topics)
        doc_topic_matrix = lda_service.fit_transform(documents)
        
        # --- สร้าง pyLDAvis HTML ถ้ามีการระบุออปชัน ---
        if export_html:
            lda_service.export_pyldavis(export_html)
            self.stdout.write(self.style.SUCCESS(f"Exported pyLDAvis HTML to: {export_html}"))

        end_time = time.time()
        execution_time = end_time - start_time

        topics_words_list = lda_service.get_top_words_list(n_top_words=10)
        topic_keywords_map = {i: ", ".join(words) for i, words in enumerate(topics_words_list)}

        # --- 3. คำนวณ NMI & Purity ---
        y_pred_hard_ids = np.argmax(doc_topic_matrix, axis=1)
        nmi = normalized_mutual_info_score(y_true_dominant, y_pred_hard_ids)
        
        cluster_to_label_map = {}
        for cid in range(n_topics):
            indices = [i for i, x in enumerate(y_pred_hard_ids) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices]
                cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
            else:
                cluster_to_label_map[cid] = "Unknown"

        y_pred_mapped = [cluster_to_label_map.get(cid, "Unknown") for cid in y_pred_hard_ids]
        purity = sum(1 for yt, yp in zip(y_true_dominant, y_pred_mapped) if yt == yp) / len(y_true_dominant) if y_true_dominant else 0

        # --- 4. คำนวณ F1 ---
        f1_scores, precision_scores, recall_scores = [], [], []

        for i, paper_item in enumerate(papers_data):
            true_labels_set = set(paper_item["true_labels"])
            pred_labels = set()
            probs = doc_topic_matrix[i]
            
            # ดึงค่าความน่าจะเป็นที่สูงที่สุดของเปเปอร์ใบนี้มาเป็นเกณฑ์ตั้งต้น
            max_prob = max(probs) if len(probs) > 0 else 0
            
            for t_id, prob in enumerate(probs):
                # Relative Threshold: Topic รอง ต้องมีน้ำหนักเกิน 0.1 "และ" ต้องมีน้ำหนักไม่น้อยกว่า 30% ของ Topic หลัก
                if prob > 0.1 and prob >= (max_prob * 0.3): 
                    mapped_label = cluster_to_label_map.get(t_id, "Unknown")
                    if mapped_label != "Unknown": pred_labels.add(mapped_label)
            
            max_tid = int(np.argmax(probs))
            if not pred_labels: pred_labels.add(cluster_to_label_map.get(max_tid, "Unknown"))

            intersection = len(true_labels_set & pred_labels)
            p = intersection / len(pred_labels) if len(pred_labels) > 0 else 0
            r = intersection / len(true_labels_set) if len(true_labels_set) > 0 else 0
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

            precision_scores.append(p)
            recall_scores.append(r)
            f1_scores.append(f1)
            
            # บันทึกคะแนนแยกรายเปเปอร์
            paper_item["predicted_top_topic_id"] = str(max_tid)
            paper_item["predicted_top_label"] = str(cluster_to_label_map.get(max_tid, "Unknown"))
            paper_item["predicted_multi_labels"] = list(pred_labels)
            paper_item["predicted_topic_keywords"] = topic_keywords_map.get(max_tid, "")
            paper_item["precision"] = p
            paper_item["recall"] = r
            paper_item["f1_score"] = f1
            paper_item["topic_distribution"] = [float(prob) for prob in probs]

        avg_f1, avg_p, avg_r = np.mean(f1_scores), np.mean(precision_scores), np.mean(recall_scores)
        diversity = lda_service.calculate_topic_diversity()
        coherence = lda_service.calculate_coherence_score(documents)

        # --- 6. แสดงผลรวม ---
        print("\n" + "="*60)
        print(f"LDA BENCHMARK RESULTS (Level {target_level})")
        print("="*60)
        print(f"{'NMI Score (Single)':<30} | {nmi:.4f}")
        print(f"{'Purity (Single)':<30} | {purity:.4f}")
        print("-"*60)
        print(f"{'Avg Precision (Multi)':<30} | {avg_p:.4f}")
        print(f"{'Avg Recall (Multi)':<30} | {avg_r:.4f}")
        print(f"{'Avg F1 Score (Multi)':<30} | {avg_f1:.4f}")
        print("-"*60)
        print(f"{'Topic Diversity':<30} | {diversity:.4f}")
        print(f"{'Topic Coherence (Cv)':<30} | {coherence:.4f}")
        print("=" * 60)
        print(f"Execution Time: {execution_time:.2f} seconds")
        print("="*60)

        print(f"\nLDA TOPIC MAPPING (First {min(10, n_topics)} Topics)")
        print("-" * 60)
        for cid in range(min(10, n_topics)):
            label = cluster_to_label_map.get(cid, "Unknown")
            words = ", ".join(topics_words_list[cid]) if cid < len(topics_words_list) else ""
            print(f"Topic {cid:<2} -> {label:<25} | Keywords: {words}")

        # --- 7. Export ---
        if export_csv:
            with open(export_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                header = [
                    'Paper ID', 'Title', 'True Top Label', 'True Multi-Labels', 
                    'Predicted Top Topic ID', 'Predicted Top Label', 'Predicted Multi-Labels',
                    'Predicted Topic Keywords', 'Precision', 'Recall', 'F1-Score'
                ]
                for t in range(n_topics): header.append(f"Topic_{t}_Prob")
                writer.writerow(header)
                
                for p in papers_data:
                    row = [
                        p.get('id', ''), p.get('title', ''), p.get('top_label', ''), 
                        ", ".join([str(x) for x in p.get('true_labels', [])]),
                        p.get('predicted_top_topic_id', ''), p.get('predicted_top_label', ''), 
                        ", ".join([str(x) for x in p.get('predicted_multi_labels', [])]),
                        p.get('predicted_topic_keywords', ''),
                        f"{p.get('precision', 0):.4f}", f"{p.get('recall', 0):.4f}", f"{p.get('f1_score', 0):.4f}"
                    ]
                    row.extend([f"{prob:.4f}" for prob in p.get('topic_distribution', [])])
                    writer.writerow(row)
            self.stdout.write(self.style.SUCCESS(f"Exported Clean CSV: {export_csv}"))

        # --- 8. Export Visualizations (UMAP & Bar Chart) ---
        if export_barchart:
            lda_service.export_top_words_barchart(export_barchart)
            self.stdout.write(self.style.SUCCESS(f"Exported Bar Chart: {export_barchart}"))
            
        if export_scatter:
            lda_service.export_document_scatter(export_scatter, y_pred_hard_ids)
            self.stdout.write(self.style.SUCCESS(f"Exported UMAP Scatter Plot: {export_scatter}"))

        if export_scatter_3d:
            lda_service.export_document_scatter_3d(export_scatter_3d, y_pred_hard_ids)
            self.stdout.write(self.style.SUCCESS(f"Exported UMAP 3D Scatter Plot: {export_scatter_3d}"))