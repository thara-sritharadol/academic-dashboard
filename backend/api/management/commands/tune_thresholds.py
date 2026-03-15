import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.lda_service import LDAService
from api.services.nmf_service import NMFService
from api.services.bertopic_service import BERTopicService # เพิ่ม Import BERTopic

class Command(BaseCommand):
    help = 'Tune Absolute and Relative Thresholds for LDA, NMF, and BERTopic to maximize F1-Score'

    def add_arguments(self, parser):
        #เพิ่ม bertopic ใน choices
        parser.add_argument('--model', type=str, choices=['lda', 'nmf', 'bertopic'], required=True, help='Model to tune')
        parser.add_argument('--input', type=str, help='Path to JSON dataset (optional)')
        parser.add_argument('--k', type=int, help='Manually set number of topics K (optional)')
        parser.add_argument('--target_level', type=int, choices=[0, 1, 2], default=1, help='Target concept level')
        parser.add_argument('--export_heatmap', type=str, default='threshold_heatmap.png', help='File path to export Heatmap PNG')
        
        #BERTopic
        parser.add_argument('--use_approx_dist', action='store_true', help='[BERTopic] Use approximate_distribution (c-TF-IDF)')
        parser.add_argument('--use_lemmatized_input', action='store_true', help='[BERTopic] Preprocess input text before embedding')

    def handle(self, *args, **options):
        model_type = options.get('model')
        input_file = options.get('input')
        k_option = options.get('k')
        target_level = options.get('target_level')
        export_heatmap = options.get('export_heatmap')
        
        use_approx_dist = options.get('use_approx_dist')
        use_lemmatized_input = options.get('use_lemmatized_input')

        documents = []
        papers_data = [] 
        y_true_dominant = [] 

        target_key_hard = f'true_label_l{target_level}'
        target_key_multi = f'multi_labels_l{target_level}'

        # --- 1. โหลดข้อมูล ---
        self.stdout.write(self.style.NOTICE(f"Loading data for {model_type.upper()} tuning..."))
        if input_file:
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
                    valid_concepts = [c for c in item['openalex_concepts'] if c.get('level') == target_level]
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
                        "true_labels": list(true_labels_set), 
                    })
            n_topics = k_option if k_option else len(set(y_true_dominant))
        else:
            papers = Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact='')
            if not papers.exists(): return
            for paper in papers:
                text = f"{paper.title} {paper.abstract}"
                concepts = paper.openalex_concepts
                true_labels_set = set()
                valid_concepts = [c for c in concepts if c.get('level') == target_level]
                true_labels_set.update([c['name'] for c in valid_concepts])
                if true_labels_set and text.strip():
                    valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                    top_label = valid_concepts[0]['name']
                    documents.append(text)
                    y_true_dominant.append(top_label)
                    papers_data.append({
                        "id": str(paper.id),
                        "true_labels": list(true_labels_set),
                    })
            n_topics = k_option if k_option else len(set(y_true_dominant))

        if not documents: 
            print("No documents found.")
            return

        # --- 2. รันโมเดลเพื่อดึง Matrix ความน่าจะเป็น ---
        y_pred_hard_ids = []
        doc_topic_matrix = None

        if model_type == 'bertopic':
            # พิเศษสำหรับ BERTopic: ถ้าไม่ระบุ --k ให้เป็น None เพื่อให้ HDBSCAN หา K เอง (Auto)
            actual_k = k_option if k_option else None
            msg_k = actual_k if actual_k else "Auto"
            self.stdout.write(self.style.NOTICE(f"Training {model_type.upper()} with {msg_k} topics..."))
            
            service = BERTopicService(n_topics=actual_k, use_approx_dist=use_approx_dist, use_lemmatized_input=use_lemmatized_input)
            topics_hard, probs = service.fit_transform(documents)
            
            if probs is None:
                print("Error: BERTopic failed to generate probabilities.")
                return
            doc_topic_matrix = probs
            y_pred_hard_ids = topics_hard # ใช้ค่า Hard Cluster ตรงๆ เพราะมี Topic -1 (Outlier)
            
            # อัปเดต n_topics เป็นจำนวนคลัสเตอร์ที่ BERTopic หาได้จริง (เพื่อใช้ในขั้นตอนถัดไป)
            n_topics = len(probs[0]) if len(probs) > 0 else 0

        else:
            # สำหรับ LDA และ NMF: บังคับใช้ K ตามที่ระบุ หรือใช้จำนวน Label จริง (Domain)
            actual_k = k_option if k_option else len(set(y_true_dominant))
            self.stdout.write(self.style.NOTICE(f"Training {model_type.upper()} with {actual_k} topics..."))
            n_topics = actual_k # อัปเดตตัวแปร n_topics

            if model_type == 'lda':
                service = LDAService(n_topics=actual_k)
                doc_topic_matrix = service.fit_transform(documents)
                y_pred_hard_ids = np.argmax(doc_topic_matrix, axis=1)
                
            elif model_type == 'nmf':
                service = NMFService(n_topics=actual_k)
                matrix = service.fit_transform(documents)
                # Normalize NMF ให้อยู่ในรูป Probability
                row_sums = matrix.sum(axis=1)
                row_sums[row_sums == 0] = 1 
                doc_topic_matrix = matrix / row_sums[:, np.newaxis]
                y_pred_hard_ids = np.argmax(doc_topic_matrix, axis=1) # ใช้ค่า Hard Cluster ตรงๆ เพราะมี -1 

        # --- 3. สร้าง Mapping ว่า Topic ไหนคือ Label อะไร ---
        cluster_to_label_map = {}
        unique_clusters = set(y_pred_hard_ids)
        for cid in unique_clusters:
            indices = [i for i, x in enumerate(y_pred_hard_ids) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices]
                cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
            else:
                cluster_to_label_map[cid] = "Unknown"

        # --- 4. เริ่มต้น GRID SEARCH วนหา Threshold ที่ดีที่สุด ---
        abs_thresholds = np.arange(0.05, 0.26, 0.05)
        rel_thresholds = np.arange(0.1, 0.6, 0.1) 
        results_matrix = np.zeros((len(abs_thresholds), len(rel_thresholds)))
        
        self.stdout.write(self.style.NOTICE("Running Grid Search..."))
        
        best_f1 = 0
        best_params = (0, 0)

        for i, abs_t in enumerate(abs_thresholds):
            for j, rel_t in enumerate(rel_thresholds):
                f1_list = []
                for doc_idx, paper_item in enumerate(papers_data):
                    true_labels_set = set(paper_item["true_labels"])
                    pred_labels = set()
                    probs = doc_topic_matrix[doc_idx]
                    
                    max_prob = max(probs) if len(probs) > 0 else 0
                    
                    for t_id, prob in enumerate(probs):
                        if prob > abs_t and prob >= (max_prob * rel_t): 
                            mapped_label = cluster_to_label_map.get(t_id, "Unknown")
                            if mapped_label != "Unknown": pred_labels.add(mapped_label)
                    
                    # ถ้าผ่านตะแกรงร่อนมาแล้วไม่ติด Topic ใดเลย (หรืออาจเป็น Outlier ใน BERTopic)
                    hard_cluster_id = int(y_pred_hard_ids[doc_idx])
                    if not pred_labels: pred_labels.add(cluster_to_label_map.get(hard_cluster_id, "Unknown"))

                    intersection = len(true_labels_set & pred_labels)
                    p = intersection / len(pred_labels) if len(pred_labels) > 0 else 0
                    r = intersection / len(true_labels_set) if len(true_labels_set) > 0 else 0
                    f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
                    f1_list.append(f1)
                
                avg_f1 = np.mean(f1_list)
                results_matrix[i, j] = avg_f1
                
                if avg_f1 > best_f1:
                    best_f1 = avg_f1
                    best_params = (abs_t, rel_t)

        # --- 5. สรุปผลลัพธ์ ---
        mode_str = ""
        if model_type == 'bertopic':
            mode_str = " [APPROX (c-TF-IDF)]" if use_approx_dist else " [HDBSCAN]"
            
        title_str = f"{model_type.upper()}{mode_str}"
            
        print("\n" + "="*60)
        print(f"GRID SEARCH RESULTS FOR {title_str}")
        print("="*60)
        print(f"Best F1-Score: {best_f1:.4f}")
        print(f"Optimal Absolute Threshold (prob > X): {best_params[0]:.2f}")
        print(f"Optimal Relative Threshold (prob >= max_prob * Y): {best_params[1]:.2f}")
        print("="*60)

        # --- 6. สร้างกราฟ Heatmap ---
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            results_matrix, 
            annot=True, 
            fmt=".4f", 
            cmap="Purples" if model_type == 'bertopic' else "YlGnBu", # เปลี่ยนสี BERTopic ให้แยกง่ายๆ
            xticklabels=np.round(rel_thresholds, 2),
            yticklabels=np.round(abs_thresholds, 2)
        )
        
        plt.xlabel("Relative Threshold (Y%)", fontsize=12, fontweight='bold')
        plt.ylabel("Absolute Threshold (X)", fontsize=12, fontweight='bold')
        plt.title(f"{title_str} Multi-label F1-Score Grid Search", fontsize=14, fontweight='bold')
        
        best_i = np.where(np.isclose(abs_thresholds, best_params[0]))[0][0]
        best_j = np.where(np.isclose(rel_thresholds, best_params[1]))[0][0]
        ax = plt.gca()
        ax.add_patch(plt.Rectangle((best_j, best_i), 1, 1, fill=False, edgecolor='red', lw=3))
        
        plt.tight_layout()
        plt.savefig(export_heatmap, dpi=300)
        plt.close()
        
        self.stdout.write(self.style.SUCCESS(f"Exported Heatmap to: {export_heatmap}"))