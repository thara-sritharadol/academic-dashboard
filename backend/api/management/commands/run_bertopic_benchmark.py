from django.core.management.base import BaseCommand
from api.models import Paper
from sklearn.metrics import normalized_mutual_info_score
from collections import Counter
import numpy as np
import spacy
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary

class Command(BaseCommand):
    help = 'Run BERTopic Benchmark with ALL Metrics (NMI, Purity, F1, Coherence, Diversity)'

    def __init__(self):
        super().__init__()
        self.nlp = None

    def _setup_spacy(self):
        """Setup Spacy & Stopwords (Logic เดียวกับ ClusteringService/LDA/NMF)"""
        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
        except OSError:
            print("Error: Spacy model 'en_core_web_sm' not found.")
            return

        academic_stopwords = [
            'paper', 'study', 'research', 'result', 'results', 'method', 'methodology',
            'proposed', 'propose', 'approach', 'based', 'using', 'used', 'use',
            'analysis', 'model', 'system', 'data', 'application', 'new', 'development',
            'performance', 'conclusion', 'abstract', 'introduction', 'work', 'time',
            'significant', 'shown', 'show', 'demonstrate', 'experiment', 'experimental',
            'university', 'department', 'author', 'et', 'al', 'figure', 'table',
            'high', 'low', 'large', 'small', 'different', 'various'
        ]
        for word in academic_stopwords:
            self.nlp.vocab[word].is_stop = True

    def spacy_tokenizer(self, text):
        if not text: return []
        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc 
                if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

    def handle(self, *args, **options):
        # --- 0. Setup NLP ---
        self._setup_spacy()
        if not self.nlp: return

        # --- 1. เตรียมข้อมูล ---
        papers = Paper.objects.exclude(cluster_id__isnull=True)\
                              .exclude(cluster_id=-1)\
                              .exclude(openalex_concepts__isnull=True)

        if not papers.exists():
            self.stdout.write(self.style.WARNING("No suitable papers found."))
            return

        print(f"Found {papers.count()} papers. Benchmarking BERTopic...")

        papers_data = [] 
        y_true_dominant = [] 
        y_pred_hard_ids = [] 
        
        # เก็บข้อมูลสำหรับคำนวณ Coherence
        all_texts_for_coherence = [] 
        cluster_keywords_map = {} # {cid: [word1, word2, ...]}

        print("Preprocessing texts for Coherence calculation (this might take a moment)...")
        
        for paper in papers:
            text = f"{paper.title} {paper.abstract}"
            concepts = paper.openalex_concepts
            
            # 1. Tokenize for Coherence (ทำสดๆ เพื่อความชัวร์)
            tokens = self.spacy_tokenizer(text)
            all_texts_for_coherence.append(tokens)

            # 2. Extract Keywords form Cluster Label
            # cluster_label format usually: "word1, word2, word3, ..."
            if paper.cluster_id not in cluster_keywords_map and paper.cluster_label:
                keywords = [k.strip() for k in paper.cluster_label.split(',')]
                cluster_keywords_map[paper.cluster_id] = keywords

            # 3. Prepare Standard Metrics Data
            true_labels_set = set()
            valid_concepts_list = []
            
            for c in concepts:
                 if c.get('level') == 1 and c.get('score', 0) > 0.3:
                     true_labels_set.add(c['name'])
                     valid_concepts_list.append(c)

            if true_labels_set: 
                valid_concepts_list.sort(key=lambda x: x.get('score', 0), reverse=True)
                top_label = valid_concepts_list[0]['name']

                y_true_dominant.append(top_label)
                y_pred_hard_ids.append(paper.cluster_id)

                papers_data.append({
                    "true_labels": true_labels_set,
                    "topic_distribution": paper.topic_distribution,
                    "cluster_id": paper.cluster_id
                })

        # --- 2. คำนวณ NMI & Purity ---
        print("\nCalculating Hard Clustering Metrics...")
        nmi = normalized_mutual_info_score(y_true_dominant, y_pred_hard_ids)
        
        cluster_to_label_map = {}
        unique_clusters = set(y_pred_hard_ids)

        for cid in unique_clusters:
            indices = [i for i, x in enumerate(y_pred_hard_ids) if x == cid]
            if indices:
                labels_in_cluster = [y_true_dominant[i] for i in indices]
                most_common = Counter(labels_in_cluster).most_common(1)[0][0]
                cluster_to_label_map[cid] = most_common
            else:
                cluster_to_label_map[cid] = "Unknown"

        y_pred_mapped = [cluster_to_label_map.get(cid, "Unknown") for cid in y_pred_hard_ids]
        correct_count = sum(1 for yt, yp in zip(y_true_dominant, y_pred_mapped) if yt == yp)
        purity = correct_count / len(y_true_dominant)

        # --- 3. คำนวณ F1 (Sample-averaged) ---
        print("Calculating Multi-label F1 Score...")
        f1_scores, precision_scores, recall_scores = [], [], []

        for paper_item in papers_data:
            true_labels = paper_item["true_labels"]
            pred_labels = set()
            dist = paper_item["topic_distribution"]
            
            if dist:
                for item in dist:
                    if item.get('prob', 0) > 0.1:
                        mapped = cluster_to_label_map.get(item.get('topic_id'), "Unknown")
                        if mapped != "Unknown": pred_labels.add(mapped)
            
            if not pred_labels:
                cid = paper_item["cluster_id"]
                mapped = cluster_to_label_map.get(cid, "Unknown")
                pred_labels.add(mapped)

            intersection = len(true_labels & pred_labels)
            p = intersection / len(pred_labels) if pred_labels else 0
            r = intersection / len(true_labels) if true_labels else 0
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

            precision_scores.append(p)
            recall_scores.append(r)
            f1_scores.append(f1)

        avg_f1 = np.mean(f1_scores)
        avg_p = np.mean(precision_scores)
        avg_r = np.mean(recall_scores)

        # --- 4. คำนวณ Topic Coherence & Diversity (ย้ายมาคำนวณตรงนี้) ---
        print("Calculating Topic Coherence (Cv) & Diversity...")
        
        # เตรียม Topics List (List of list of words)
        topics_words_list = []
        # เรียงตาม Cluster ID เพื่อความชัวร์ (แม้ Coherence ไม่แคร์ order แต่ Diversity แคร์จำนวน)
        sorted_cids = sorted(cluster_keywords_map.keys())
        for cid in sorted_cids:
            topics_words_list.append(cluster_keywords_map[cid])

        # 4.1 Coherence
        coherence_score = 0.0
        try:
            dictionary = Dictionary(all_texts_for_coherence)
            cm = CoherenceModel(
                topics=topics_words_list, 
                texts=all_texts_for_coherence, 
                dictionary=dictionary, 
                coherence='c_v'
            )
            coherence_score = cm.get_coherence()
        except Exception as e:
            print(f"Error calculating coherence: {e}")

        # 4.2 Diversity
        unique_words = set()
        total_words = 0
        for words in topics_words_list:
            unique_words.update(words)
            total_words += len(words)
        
        diversity_score = len(unique_words) / total_words if total_words > 0 else 0

        # --- 5. แสดงผลรวม ---
        print("\n" + "="*60)
        print("📊 BERTopic BENCHMARK RESULTS (Complete & Standardized)")
        print("="*60)
        print(f"{'Metric':<30} | {'Score':<10}")
        print("-" * 45)
        print(f"{'NMI Score':<30} | {nmi:.4f}")
        print(f"{'Purity':<30} | {purity:.4f}")
        print("-" * 45)
        print(f"{'Sample-avg Precision':<30} | {avg_p:.4f}")
        print(f"{'Sample-avg Recall':<30} | {avg_r:.4f}")
        print(f"{'Sample-avg F1 Score':<30} | {avg_f1:.4f}") 
        print("-" * 45)
        print(f"{'Topic Diversity':<30} | {diversity_score:.4f}")
        print(f"{'Topic Coherence (Cv)':<30} | {coherence_score:.4f}")
        print("="*60)

        # แสดง Mapping
        print("\n🧐 BERTopic MAPPING (Sorted by ID)")
        print("-" * 60)
        for cid in sorted_cids:
            label = cluster_to_label_map.get(cid, "Unknown")
            words = ", ".join(cluster_keywords_map.get(cid, []))
            if len(words) > 50: words = words[:47] + "..."
            print(f"Topic {cid:<2} -> {label:<25} | Keywords: {words}")