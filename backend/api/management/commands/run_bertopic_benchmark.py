import csv
import json
import time
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.bertopic_service import BERTopicService
from sklearn.metrics import normalized_mutual_info_score
from collections import Counter
import numpy as np

class Command(BaseCommand):
    help = 'Run BERTopic Benchmark with Time Tracking and Per-paper Metrics Export'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, help='Path to JSON dataset (optional)')
        parser.add_argument('--k', type=int, help='Manually reduce number of topics K (optional)')

        parser.add_argument('--threshold', type=float, default=0.3, help='Score threshold for multi-labels')
        parser.add_argument('--abs_threshold', type=float, default=0.1, help='Absolute probability threshold (e.g., 0.1)')
        parser.add_argument('--rel_threshold', type=float, default=0.3, help='Relative threshold multiplier (e.g., 0.3)')

        parser.add_argument('--use_approx_dist', action='store_true', help='Use approximate_distribution (c-TF-IDF) instead of HDBSCAN probabilities')
        parser.add_argument('--use_lemmatized_input', action='store_true', help='Preprocess input text (lemmatization/stopwords) before passing to Specter 2')

        parser.add_argument('--target_level', type=int, choices=[0, 1, 2], default=1, help='Target concept level')

        parser.add_argument('--export_json', type=str, help='File path to export results as JSON')
        parser.add_argument('--export_csv', type=str, help='File path to export results as CSV')
        parser.add_argument('--export_barchart', type=str, help='File path to export Custom Bar Chart (e.g., bertopic_bar.png)')
        parser.add_argument('--export_scatter', type=str, help='File path to export Custom UMAP Scatter Plot (e.g., bertopic_scatter.png)')
        parser.add_argument('--export_scatter_3d', type=str, help='File path to export Custom UMAP 3D Scatter Plot as HTML (e.g., bertopic_scatter_3d.html)')
        parser.add_argument('--export_true_scatter_3d', type=str, help='File path to export Ground Truth UMAP 3D (e.g., true_scatter_3d.html)')

        parser.add_argument('--group_multi', action='store_true', help='Group all multi-label papers into a single "Multi-label" color')

        parser.add_argument('--export_html', type=str, help='Prefix path to export BERTopic HTMLs (e.g., bertopic_html)')

    def handle(self, *args, **options):
        input_file = options.get('input')
        k_option = options.get('k')
        threshold = options.get('threshold')
        abs_threshold = options.get('abs_threshold')
        rel_threshold = options.get('rel_threshold')
        target_level = options.get('target_level')
        export_json = options.get('export_json')
        export_csv = options.get('export_csv')
        use_approx_dist = options.get('use_approx_dist')
        use_lemmatized_input = options.get('use_lemmatized_input')
        export_barchart = options.get('export_barchart') 
        export_scatter = options.get('export_scatter') 
        export_scatter_3d = options.get('export_scatter_3d')
        export_true_scatter_3d = options.get('export_true_scatter_3d')
        group_multi = options.get('group_multi')
        export_html = options.get('export_html')         

        documents = []
        papers_data = [] 
        y_true_dominant = [] 
        target_key_hard = f'true_label_l{target_level}'
        target_key_multi = f'multi_labels_l{target_level}'

        if input_file:
            self.stdout.write(self.style.NOTICE(f"Loading data from JSON: {input_file}"))
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                text = item.get('text', '')
                if not text: text = f"{item.get('title', '')} {item.get('abstract', '')}"
                true_labels_set = set()
                top_label = item.get(target_key_hard)
                if target_key_multi in item and isinstance(item[target_key_multi], list):
                    true_labels_set = set(item[target_key_multi])
                elif 'openalex_concepts' in item:
                    valid_concepts = [c for c in item['openalex_concepts'] if c.get('level') == target_level and c.get('score', 0) >= threshold]
                    true_labels_set.update([c['name'] for c in valid_concepts])
                    if valid_concepts and not top_label:
                        valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                        top_label = valid_concepts[0]['name']
                else:
                    if top_label: true_labels_set.add(top_label)

                if true_labels_set and top_label and text.strip():
                    documents.append(text) 
                    y_true_dominant.append(top_label)
                    papers_data.append({
                        "id": str(item.get('id', 'N/A')),
                        "title": str(item.get('title', 'Unknown Title')).replace('\n', ' ').replace('\r', ''),
                        "true_labels": list(true_labels_set), 
                        "top_label": str(top_label)
                    })
        else:
            self.stdout.write(self.style.NOTICE(f"Loading data from DB..."))
            papers = Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact='')
            if not papers.exists(): return
            for paper in papers:
                text = f"{paper.title} {paper.abstract}"
                concepts = paper.openalex_concepts
                true_labels_set = set()
                valid_concepts = [c for c in concepts if c.get('level') == target_level and c.get('score', 0) >= threshold]
                true_labels_set.update([c['name'] for c in valid_concepts])
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

        if not documents: return

        # --- 2. Run BERTopic Service (พร้อมจับเวลา) ---
        start_time = time.time()
        #  3. ส่งตัวแปรเข้าไปตั้งค่า
        bertopic_service = BERTopicService(n_topics=k_option, use_approx_dist=use_approx_dist, use_lemmatized_input=use_lemmatized_input)
        topics, probs = bertopic_service.fit_transform(documents)
        end_time = time.time()
        execution_time = end_time - start_time

        if probs is None: return
        n_valid_topics = len(probs[0])

        topics_words_list = bertopic_service.get_top_words_list(n_top_words=10)
        topic_keywords_map = {i: ", ".join(words) for i, words in enumerate(topics_words_list)}
        topic_keywords_map[-1] = "Outlier"

        # --- 3. คำนวณ NMI & Purity ---
        nmi = normalized_mutual_info_score(y_true_dominant, topics)
        cluster_to_label_map = {}
        unique_clusters = set(topics)
        for cid in unique_clusters:
            indices = [i for i, x in enumerate(topics) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices]
                cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
            else:
                cluster_to_label_map[cid] = "Unknown"

        y_pred_mapped = [cluster_to_label_map.get(cid, "Unknown") for cid in topics]
        purity = sum(1 for yt, yp in zip(y_true_dominant, y_pred_mapped) if yt == yp) / len(y_true_dominant) if y_true_dominant else 0

        # --- 4. คำนวณ F1 ---
        f1_scores, precision_scores, recall_scores = [], [], []

        for i, paper_item in enumerate(papers_data):
            true_labels_set = set(paper_item["true_labels"])
            pred_labels = set()
            doc_probs = probs[i]
            
            max_prob = max(doc_probs) if len(doc_probs) > 0 else 0
            
            for t_id, prob in enumerate(doc_probs):
                if prob > abs_threshold and prob >= (max_prob * rel_threshold): 
                    mapped_label = cluster_to_label_map.get(t_id, "Unknown")
                    if mapped_label != "Unknown": pred_labels.add(mapped_label)
            
            hard_cluster_id = int(topics[i])
            if not pred_labels: pred_labels.add(cluster_to_label_map.get(hard_cluster_id, "Unknown"))

            intersection = len(true_labels_set & pred_labels)
            p = intersection / len(pred_labels) if len(pred_labels) > 0 else 0
            r = intersection / len(true_labels_set) if len(true_labels_set) > 0 else 0
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

            precision_scores.append(p)
            recall_scores.append(r)
            f1_scores.append(f1)
            
            paper_item["predicted_top_topic_id"] = str(hard_cluster_id)
            paper_item["predicted_top_label"] = str(cluster_to_label_map.get(hard_cluster_id, "Unknown"))
            paper_item["predicted_multi_labels"] = list(pred_labels)
            paper_item["predicted_topic_keywords"] = topic_keywords_map.get(hard_cluster_id, "")
            paper_item["precision"] = p
            paper_item["recall"] = r
            paper_item["f1_score"] = f1
            paper_item["topic_distribution"] = [float(prob) for prob in doc_probs]

        avg_f1, avg_p, avg_r = np.mean(f1_scores), np.mean(precision_scores), np.mean(recall_scores)
        diversity = bertopic_service.calculate_topic_diversity()
        coherence = bertopic_service.calculate_coherence_score(documents)

        # --- 6. แสดงผลรวม ---
        print("\n" + "="*60)
        mode_str = "(Approx Dist)" if use_approx_dist else "(HDBSCAN Prob)"
        lemma_str = "[LEMMATIZED INPUT]" if use_lemmatized_input else "[RAW TEXT]"
        print(f"BERTopic BENCHMARK RESULTS {mode_str} {lemma_str} - Level {target_level}")
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
        print("-" * 60)
        print(f"Execution Time: {execution_time:.2f} seconds")
        print("="*60)

        print(f"\nBERTopic TOPIC MAPPING (First {min(10, n_valid_topics)} Valid Topics)")
        print("-" * 60)
        for cid in range(min(10, n_valid_topics)):
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
                for t in range(n_valid_topics): header.append(f"Topic_{t}_Prob")
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

        # --- 8. Export Visualizations ---
        if export_barchart:
            bertopic_service.export_top_words_barchart(export_barchart)
            self.stdout.write(self.style.SUCCESS(f"Exported Bar Chart: {export_barchart}"))
            
        if export_scatter:
            bertopic_service.export_document_scatter(export_scatter, topics)
            self.stdout.write(self.style.SUCCESS(f"Exported UMAP Scatter Plot: {export_scatter}"))

        if export_scatter_3d:
            bertopic_service.export_document_scatter_3d(export_scatter_3d, topics)
            self.stdout.write(self.style.SUCCESS(f"Exported UMAP 3D Scatter Plot HTML: {export_scatter_3d}"))

        if export_true_scatter_3d:
            true_labels_for_plot = []
            
            for p in papers_data:
                labels = p.get('true_labels', [])
                
                if len(labels) > 1:
                    # เช็คสวิตช์ว่าต้องการยุบรวมสีไหม
                    if group_multi:
                        true_labels_for_plot.append("Multi-label (Interdisciplinary)")
                        sorted_labels = sorted([str(l) for l in labels])
                        compound_label = " + ".join(sorted_labels)
                        true_labels_for_plot.append(compound_label)
                elif len(labels) == 1:
                    true_labels_for_plot.append(str(labels[0]))
                else:
                    true_labels_for_plot.append("Unknown")

            # ส่งไปพล็อต
            bertopic_service.export_ground_truth_scatter_3d(export_true_scatter_3d, true_labels_for_plot)
            self.stdout.write(self.style.SUCCESS(f"Exported Ground Truth 3D Scatter Plot: {export_true_scatter_3d}"))

        if export_html:
            bertopic_service.export_bertopic_html(export_html)
            self.stdout.write(self.style.SUCCESS(f"Exported BERTopic Interactive HTMLs: {export_html}_*.html"))