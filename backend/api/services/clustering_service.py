import logging
import numpy as np
import pandas as pd
import spacy
import gensim.corpora as corpora
from gensim.models.coherencemodel import CoherenceModel
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from scipy.stats import entropy
from api.models import Paper

logger = logging.getLogger(__name__)

class ClusteringService:
    def __init__(self):
        self.nlp = None
        self.topic_model = None
        self.topics = None
        self.probs = None
        self.abstracts = []
        self.paper_ids = []
        self.vectorizer_model = None
        
        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
            self._setup_stopwords()
        except OSError:
            logger.error("Spacy model 'en_core_web_sm' not found.")
            raise

    def _setup_stopwords(self):
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

    def load_data(self):
        papers_qs = Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact='')
        if not papers_qs.exists():
            return False
            
        data = list(papers_qs.values('id', 'abstract'))
        df = pd.DataFrame(data)
        self.abstracts = df['abstract'].tolist()
        self.paper_ids = df['id'].tolist()
        return True

    def perform_clustering(self):
        self.vectorizer_model = CountVectorizer(tokenizer=self.spacy_tokenizer, ngram_range=(1, 2))
        
        umap_model = UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric='cosine',
            random_state=42,
            low_memory=True
        )

        self.topic_model = BERTopic(
            umap_model=umap_model,
            min_topic_size=5,
            embedding_model="allenai/specter",
            vectorizer_model=self.vectorizer_model,
            calculate_probabilities=True,
            verbose=True,
            top_n_words=20
        )

        self.topics, self.probs = self.topic_model.fit_transform(self.abstracts)
        return True

    def evaluate_model(self):
        """คำนวณ Coherence, Diversity และ System Entropy"""
        if not self.topic_model:
            return None

        #Prepare Gensim Dictionary
        analyzer = self.vectorizer_model.build_analyzer()
        tokens = [analyzer(doc) for doc in self.abstracts]
        id2word = corpora.Dictionary(tokens)

        #Extract Topics
        topic_info = self.topic_model.get_topic_info()
        topic_words_list = []
        topic_ids = []
        
        for t_id in topic_info['Topic']:
            if t_id != -1:
                words = [word for word, _ in self.topic_model.get_topic(t_id)[:10]]
                topic_words_list.append(words)
                topic_ids.append(t_id)

        #Calculate Coherence
        mean_cv = 0
        per_topic_coherence = []
        
        if topic_words_list:
            cm = CoherenceModel(topics=topic_words_list, texts=tokens, dictionary=id2word, coherence='c_v')
            mean_cv = cm.get_coherence()
            
            for idx, words in enumerate(topic_words_list):
                cm_local = CoherenceModel(topics=[words], texts=tokens, dictionary=id2word, coherence='c_v')
                per_topic_coherence.append({
                    "topic_id": topic_ids[idx],
                    "words": ", ".join(words[:5]),
                    "coherence_score": cm_local.get_coherence()
                })

        #Calculate Diversity
        diversity_score = self._calculate_diversity(top_n=10)

        #Calculate System Entropy (Mean Entropy)
        system_entropy = 0.0
        if self.probs is not None:
            #Calculate the entropy of all the papers and then find the average.
            all_entropies = entropy(self.probs, axis=1)
            system_entropy = np.mean(all_entropies)

        return {
            "mean_coherence": mean_cv,
            "diversity_score": diversity_score,
            "system_entropy": system_entropy,
            "detailed_coherence": per_topic_coherence
        }

    def _calculate_diversity(self, top_n=10):
        keys = []
        topic_info = self.topic_model.get_topic_info()
        for topic_id in topic_info['Topic']:
            if topic_id != -1:
                topic_data = self.topic_model.get_topic(topic_id)
                if topic_data:
                    words = [word for word, _ in topic_data]
                    keys.append(words[:top_n])
                    
        flattened_keys = [item for sublist in keys for item in sublist]
        unique_keys = set(flattened_keys)
        
        if len(flattened_keys) == 0: return 0
        return len(unique_keys) / len(flattened_keys)

    def save_results(self):
        if not self.topic_model: return 0

        topic_info = self.topic_model.get_topic_info()
        topic_label_map = {}
        for index, row in topic_info.iterrows():
            t_id = row['Topic']
            if t_id != -1:
                keywords = [word for word, score in self.topic_model.get_topic(t_id)[:10]]
                topic_label_map[t_id] = ", ".join(keywords)
            else:
                topic_label_map[-1] = "Outlier"

        #Calculate Entropy per Paper for Recording (PE).
        paper_entropies = [0.0] * len(self.paper_ids)
        if self.probs is not None:
            paper_entropies = entropy(self.probs, axis=1)

        papers_to_update = []
        paper_objects_map = {p.id: p for p in Paper.objects.filter(id__in=self.paper_ids)}

        for i, p_id in enumerate(self.paper_ids):
            paper = paper_objects_map.get(p_id)
            if not paper: continue

            dist_list = []
            if self.probs is not None:
                try:
                    current_probs = self.probs[i]
                    if isinstance(current_probs, np.ndarray):
                        top_indices = current_probs.argsort()[-5:][::-1]
                        for topic_idx in top_indices:
                            score = float(current_probs[topic_idx])
                            if score > 0.01:
                                dist_list.append({
                                    "topic_id": int(topic_idx),
                                    "label": topic_label_map.get(topic_idx, "Unknown"),
                                    "prob": round(score, 4)
                                })
                except Exception:
                    pass

            main_cluster_id = int(self.topics[i])
            paper.cluster_id = main_cluster_id
            paper.cluster_label = topic_label_map.get(main_cluster_id, "Outlier")
            paper.topic_distribution = dist_list
            
            #Save Entropy
            ent_val = paper_entropies[i]
            if np.isnan(ent_val): ent_val = 0.0
            paper.entropy = float(ent_val)
            
            papers_to_update.append(paper)

        batch_size = 500
        for start in range(0, len(papers_to_update), batch_size):
            end = start + batch_size
            Paper.objects.bulk_update(
                papers_to_update[start:end], 
                ['cluster_id', 'cluster_label', 'topic_distribution', 'entropy']
            )
            
        return len(papers_to_update)