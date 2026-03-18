import time
import numpy as np
from collections import Counter
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.bertopic_service import BERTopicService

class Command(BaseCommand):
    help = 'Apply BERTopic clustering with Auto-Tuning Thresholds and save to DB'

    def add_arguments(self, parser):
        parser.add_argument('--k', type=int, help='Number of topics K (leave empty for Auto)')
        parser.add_argument('--use_approx_dist', action='store_true', default=True, help='Use c-TF-IDF')
        parser.add_argument('--use_lemmatized_input', action='store_true', help='Preprocess text')
        parser.add_argument('--auto_tune', action='store_true', help='Automatically find best thresholds before applying')
        parser.add_argument('--abs_threshold', type=float, default=0.1, help='Manual absolute threshold')
        parser.add_argument('--rel_threshold', type=float, default=0.3, help='Manual relative threshold')

    def handle(self, *args, **options):
        k_option = options.get('k')
        use_approx_dist = options.get('use_approx_dist')
        use_lemmatized_input = options.get('use_lemmatized_input')
        auto_tune = options.get('auto_tune')
        
        abs_threshold = options.get('abs_threshold')
        rel_threshold = options.get('rel_threshold')

        self.stdout.write(self.style.NOTICE("Fetching papers from database..."))
        papers = list(Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact=''))
        if not papers: return

        documents = []
        true_labels_list = []
        
        for paper in papers:
            text = f"{paper.title} {paper.abstract}".strip()
            documents.append(text)
            
            concepts = paper.openalex_concepts if isinstance(paper.openalex_concepts, list) else []
            valid_concepts = [c['name'] for c in concepts if c.get('level') == 1 and c.get('score', 0) >= 0.3]
            true_labels_list.append(set(valid_concepts))

        self.stdout.write(self.style.NOTICE(f"Found {len(documents)} papers. Training BERTopic..."))
        start_time = time.time()

        bertopic_service = BERTopicService(n_topics=k_option, use_approx_dist=use_approx_dist, use_lemmatized_input=use_lemmatized_input)
        topics, probs = bertopic_service.fit_transform(documents)

        topics_words_list = bertopic_service.get_top_words_list(n_top_words=5)
        topic_labels = {t_id: f"Topic {t_id}: {', '.join(words)}" if words else f"Topic {t_id}: Unknown" for t_id, words in enumerate(topics_words_list)}
        topic_labels[-1] = "Outlier / Noise"

        if auto_tune:
            self.stdout.write(self.style.WARNING("\nRunning Auto-Tune to find best Multi-label thresholds..."))
            
            # 1. Create a map showing which cluster best matches which label.
            cluster_to_label_map = {}
            for cid in set(topics):
                labels_in_cluster = []
                for idx, t in enumerate(topics):
                    if t == cid and true_labels_list[idx]:
                        # Pull the label with the highest score from that paper and vote.
                        top_label = list(true_labels_list[idx])[0] 
                        labels_in_cluster.append(top_label)
                if labels_in_cluster:
                    cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
                else:
                    cluster_to_label_map[cid] = "Unknown"

            # 2. Grid Search find max F1
            best_f1 = 0
            abs_range = [0.05, 0.10, 0.15, 0.20, 0.25]
            rel_range = [0.1, 0.2, 0.3, 0.4, 0.5]
            
            for a_thresh in abs_range:
                for r_thresh in rel_range:
                    f1_scores = []
                    for i, doc_probs in enumerate(probs):
                        true_set = true_labels_list[i]
                        if not true_set: continue # Skip papers that don't provide answers.
                        
                        pred_set = set()
                        max_prob = max(doc_probs) if len(doc_probs) > 0 else 0
                        for t_id, prob in enumerate(doc_probs):
                            if prob > a_thresh and prob >= (max_prob * r_thresh):
                                mapped = cluster_to_label_map.get(t_id, "Unknown")
                                if mapped != "Unknown": pred_set.add(mapped)
                        
                        if not pred_set: pred_set.add(cluster_to_label_map.get(int(topics[i]), "Unknown"))
                        
                        intersection = len(true_set & pred_set)
                        p = intersection / len(pred_set) if len(pred_set) > 0 else 0
                        r = intersection / len(true_set) if len(true_set) > 0 else 0
                        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
                        f1_scores.append(f1)
                        
                    avg_f1 = np.mean(f1_scores) if f1_scores else 0
                    if avg_f1 > best_f1:
                        best_f1 = avg_f1
                        abs_threshold = a_thresh
                        rel_threshold = r_thresh
            
            self.stdout.write(self.style.SUCCESS(f"Auto-Tune Complete! Best F1: {best_f1:.4f}"))
            self.stdout.write(self.style.SUCCESS(f"Selected Absolute Threshold: {abs_threshold}"))
            self.stdout.write(self.style.SUCCESS(f"Selected Relative Threshold: {rel_threshold}\n"))

        self.stdout.write(self.style.NOTICE("Applying thresholds and saving to DB..."))
        papers_to_update = []
        for idx, paper in enumerate(papers):
            doc_probs = probs[idx]
            hard_cluster_id = int(topics[idx])
            
            pred_multi_labels = set()
            max_prob = max(doc_probs) if len(doc_probs) > 0 else 0
            
            for t_id, prob in enumerate(doc_probs):
                if prob > abs_threshold and prob >= (max_prob * rel_threshold):
                    pred_multi_labels.add(topic_labels.get(t_id, f"Topic {t_id}"))
            
            if not pred_multi_labels:
                pred_multi_labels.add(topic_labels.get(hard_cluster_id, "Outlier"))

            paper.cluster_id = hard_cluster_id
            paper.cluster_label = topic_labels.get(hard_cluster_id, "Outlier")
            paper.predicted_multi_labels = list(pred_multi_labels)
            paper.topic_distribution = [float(p) for p in doc_probs]
            
            papers_to_update.append(paper)

        Paper.objects.bulk_update(papers_to_update, ['cluster_id', 'cluster_label', 'predicted_multi_labels', 'topic_distribution'])

        self.stdout.write(self.style.SUCCESS(
            f"Database updated! ({len(papers_to_update)} papers)\n"
            f"Total execution time: {time.time() - start_time:.2f} seconds."
        ))