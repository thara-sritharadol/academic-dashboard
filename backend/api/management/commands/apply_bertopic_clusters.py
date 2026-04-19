import os
import json
import numpy as np
from collections import Counter
from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Paper
from api.pipelines.bertopic_service import BERTopicService 
from api.pipelines.gemini_service import GeminiNamingService

class Command(BaseCommand):
    help = "Run BERTopic, auto-tune multi-label thresholds via Grid Search, and use Gemini LLM for naming"

    def add_arguments(self, parser):
        parser.add_argument("--gemini_key", type=str, help="Gemini API Key for auto-naming topics")
        parser.add_argument("--k_topics", type=int, default=None, help="Force number of topics (default: None for auto-detect)")
        parser.add_argument("--auto_tune", action="store_true", help="Auto-tune multi-label thresholds (Abs/Rel) via Grid Search")

    def handle(self, *args, **options):
        auto_tune = options.get("auto_tune")
        gemini_key = options.get("gemini_key")
        k_topics = options.get("k_topics")

        self.stdout.write(self.style.NOTICE("1. Fetching papers from Database..."))
        # Include the openalex_concepts field to use as ground truth for tuning.
        papers = list(Paper.objects.exclude(abstract__isnull=True).exclude(abstract="").values('id', 'title', 'abstract', 'openalex_concepts'))
        
        if not papers:
            self.stdout.write(self.style.ERROR("No papers with abstracts found."))
            return

        docs = [f"{p['title']}. {p['abstract']}" for p in papers]
        paper_ids = [p['id'] for p in papers]

        self.stdout.write(self.style.NOTICE(f"2. Training BERTopic (K={k_topics if k_topics else 'Auto'})..."))
        bertopic_service = BERTopicService(
            n_topics=k_topics,
            use_approx_dist=True,
            use_lemmatized_input=False
        )
        topics, probs = bertopic_service.fit_transform(docs)

        # Threshold Configuration
        # The default setting in case auto_tune is not decleared or an error occurs.
        abs_threshold = 0.10
        rel_threshold = 0.10

        if auto_tune:
            self.stdout.write(self.style.NOTICE("-> [Auto-Tune] Running Grid Search to find optimal thresholds..."))
            best_abs, best_rel = self.tune_thresholds(papers, topics, probs)
            if best_abs is not None and best_rel is not None:
                abs_threshold, rel_threshold = best_abs, best_rel
                self.stdout.write(self.style.SUCCESS(f"-> [Auto-Tune] Optimal Thresholds Found: Abs = {abs_threshold:.2f}, Rel = {rel_threshold:.2f}"))
            else:
                self.stdout.write(self.style.WARNING("-> [Auto-Tune] Failed to find threshold (No Ground Truth). Using Defaults."))
        else:
            self.stdout.write(self.style.NOTICE(f"-> Using Default Thresholds: Abs = {abs_threshold:.2f}, Rel = {rel_threshold:.2f}"))

        # Assigning LLM Names
        self.stdout.write(self.style.NOTICE("4. Assigning LLM Names..."))
        llm_names = {}
        if gemini_key:
            gemini_service = GeminiNamingService(api_key=gemini_key)
            llm_names = gemini_service.generate_topic_names(bertopic_service.topic_model)
        else:
            self.stdout.write(self.style.WARNING("No Gemini Key provided, using keywords instead."))

        # Updating Database
        self.stdout.write(self.style.NOTICE("5. Updating Database..."))
        updated_count = 0
        for i, paper_id in enumerate(tqdm(paper_ids, desc="Saving to DB")):
            topic_id = topics[i]
            paper_prob = probs[i] if probs is not None else []
            distribution_list = []

            if len(paper_prob) > 0:
                distribution_list = [float(prob) for prob in paper_prob]

            if topic_id == -1:
                cluster_label = "Outlier / Noise"
            else:
                topic_str_id = str(topic_id)
                if topic_str_id in llm_names:
                    cluster_label = f"Topic {topic_id}: {llm_names[topic_str_id]}"
                else:
                    words = [word for word, _ in bertopic_service.topic_model.get_topic(topic_id)][:5]
                    cluster_label = f"Topic {topic_id}: {', '.join(words)}"

            multi_labels = [cluster_label]
            
            if topic_id != -1 and len(paper_prob) > 0:
                max_prob = max(paper_prob)
                for alt_topic_id, prob in enumerate(paper_prob):
                    if alt_topic_id != topic_id and prob > abs_threshold and prob >= (max_prob * rel_threshold):
                        alt_str_id = str(alt_topic_id)
                        if alt_str_id in llm_names:
                            alt_label = f"Topic {alt_topic_id}: {llm_names[alt_str_id]}"
                        else:
                            alt_words = [word for word, _ in bertopic_service.topic_model.get_topic(alt_topic_id)][:5]
                            alt_label = f"Topic {alt_topic_id}: {', '.join(alt_words)}"
                        multi_labels.append(alt_label)

            raw_keywords = []
            if topic_id != -1:
                raw_keywords = [word for word, _ in bertopic_service.topic_model.get_topic(topic_id)][:10]

            Paper.objects.filter(id=paper_id).update(
                cluster_id=topic_id,
                cluster_label=cluster_label,
                predicted_multi_labels=multi_labels,
                topic_keywords=raw_keywords,
                topic_distribution=distribution_list
            )
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully clustered and updated {updated_count} papers!"))

    def tune_thresholds(self, papers, topics, probs, target_level=0, score_threshold=0.3):
        y_true_dominant = []
        papers_data = []

        # Prepare Ground Truth data.
        for item in papers:
            true_labels_set = set()
            top_label = None
            
            concepts = item.get('openalex_concepts') or []
            if isinstance(concepts, str):
                try:
                    concepts = json.loads(concepts)
                except:
                    concepts = []

            valid_concepts = []
            for c in concepts:
                if c.get('level') == target_level and c.get('score', 0) >= score_threshold:
                    true_labels_set.add(c['name'])
                    valid_concepts.append(c)
                    
            if valid_concepts:
                valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                top_label = valid_concepts[0]['name']

            y_true_dominant.append(top_label)
            papers_data.append({'true_labels': list(true_labels_set)})

        has_ground_truth = any(len(p['true_labels']) > 0 for p in papers_data)
        if not has_ground_truth:
            return None, None

        # Cluster to Label Mapping
        cluster_to_label_map = {}
        unique_clusters = set(topics)
        for cid in unique_clusters:
            indices = [i for i, x in enumerate(topics) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices if y_true_dominant[i] is not None]
                if labels_in_cluster:
                    cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
                else:
                    cluster_to_label_map[cid] = 'Unknown'
            else:
                cluster_to_label_map[cid] = 'Unknown'

        # Grid Search to find Threshold
        abs_thresholds = np.round(np.arange(0.05, 0.26, 0.05), 2)
        rel_thresholds = np.round(np.arange(0.1, 0.6, 0.1), 2)
        
        best_f1 = 0.0
        best_params = (0.10, 0.10)

        for abs_t in abs_thresholds:
            for rel_t in rel_thresholds:
                f1_list = []
                for doc_idx, paper_item in enumerate(papers_data):
                    true_labels_set = set(paper_item['true_labels'])
                    if not true_labels_set: 
                        continue 
                    
                    pred_labels = set()
                    paper_probs = probs[doc_idx]
                    max_prob = max(paper_probs) if len(paper_probs) > 0 else 0

                    for t_id, prob in enumerate(paper_probs):
                        if prob > abs_t and prob >= (max_prob * rel_t):
                            mapped_label = cluster_to_label_map.get(t_id, 'Unknown')
                            if mapped_label != 'Unknown':
                                pred_labels.add(mapped_label)

                    hard_cluster_id = int(topics[doc_idx])
                    if not pred_labels:
                        pred_labels.add(cluster_to_label_map.get(hard_cluster_id, 'Unknown'))

                    intersection = len(true_labels_set & pred_labels)
                    p = intersection / len(pred_labels) if pred_labels else 0
                    r = intersection / len(true_labels_set) if true_labels_set else 0
                    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
                    f1_list.append(f1)

                avg_f1 = np.mean(f1_list) if f1_list else 0
                if avg_f1 > best_f1:
                    best_f1 = avg_f1
                    best_params = (abs_t, rel_t)

        return best_params[0], best_params[1]