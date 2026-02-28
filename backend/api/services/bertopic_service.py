import logging
import numpy as np
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from bertopic import BERTopic
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import umap as umap_learn 

logger = logging.getLogger(__name__)

class BERTopicService:
    # 💡 1. เพิ่มตัวแปร use_approx_dist (ค่าเริ่มต้นคือ False เพื่อให้พฤติกรรมเดิมทำงานปกติ)
    def __init__(self, n_topics=None, use_approx_dist=False):
        self.n_topics = n_topics 
        self.use_approx_dist = use_approx_dist
        self.nlp = None
        self.topic_model = None
        self.topics = None
        self.probs = None
        
        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
            self._setup_stopwords()
        except OSError:
            logger.error("Spacy model 'en_core_web_sm' not found.")
            raise

        self.vectorizer_model = CountVectorizer(
            tokenizer=self.spacy_tokenizer, 
            ngram_range=(1, 2)
        )

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

    def fit_transform(self, documents):
        print(f"Training BERTopic (Target Topics: {self.n_topics if self.n_topics else 'Auto'})...")
        
        # 💡 2. พิมพ์แจ้งเตือนว่ากำลังใช้ Mode ไหน
        if self.use_approx_dist:
            print("Mode: approximate_distribution (c-TF-IDF for Soft Clustering)")
        else:
            print("Mode: calculate_probabilities (HDBSCAN for Confidence Score)")

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
            embedding_model="allenai/specter2_base",
            vectorizer_model=self.vectorizer_model,
            # 💡 3. ถ้าใช้ Approx Dist เราจะปิดการหา Prob ของ HDBSCAN เพื่อประหยัดเวลาและหน่วยความจำ
            calculate_probabilities=not self.use_approx_dist,
            nr_topics=self.n_topics if self.n_topics else "auto",
            verbose=True,
            top_n_words=10
        )

        # ฝึกสอนโมเดล (ถ้า calculate_probabilities=False ตัว probs จะคืนค่าเป็น None)
        self.topics, self.probs = self.topic_model.fit_transform(documents)

        # 💡 4. ถ้าเปิดโหมด Approx Dist ให้คำนวณ Distribution แยกต่างหาก แล้วเอาไปทับตัวแปร probs
        if self.use_approx_dist:
            print("Calculating approximate topic distributions (c-TF-IDF)...")
            # 4.1 ปรับลด min_similarity ลง เพื่อดึงเศษคะแนนที่ซ่อนอยู่ออกมา
            topic_distr, _ = self.topic_model.approximate_distribution(
                documents, 
                min_similarity=0,
                window=4
                
            )
            
            # 4.2 ทำ Normalization ให้ผลรวมแต่ละเปเปอร์เข้าใกล้ 1.0 เสมอ (เหมือน NMF)
            row_sums = topic_distr.sum(axis=1)
            row_sums[row_sums == 0] = 1 # ป้องกัน Error หารด้วย 0 สำหรับเปเปอร์ที่ Outlier จริงๆ
            topic_distr = topic_distr / row_sums[:, np.newaxis]
            
            self.probs = topic_distr

        return self.topics, self.probs

    def get_top_words_list(self, n_top_words=10):
        topics_words = []
        n_valid_topics = len(self.probs[0]) if self.probs is not None and len(self.probs) > 0 else 0
        
        for t_id in range(n_valid_topics):
            if t_id in self.topic_model.get_topics():
                words = [word for word, _ in self.topic_model.get_topic(t_id)[:n_top_words]]
                topics_words.append(words)
            else:
                topics_words.append([])
        return topics_words

    def calculate_topic_diversity(self, n_top_words=10):
        topics_words = self.get_top_words_list(n_top_words)
        unique_words = set()
        total_words = 0
        for topic in topics_words:
            if not topic: continue
            unique_words.update(topic)
            total_words += len(topic)
        if total_words == 0: return 0
        return len(unique_words) / total_words

    def calculate_coherence_score(self, documents):
        print("Calculating BERTopic Coherence...")
        tokenized_docs = [self.spacy_tokenizer(doc) for doc in documents]
        topics_words = [words for words in self.get_top_words_list(n_top_words=10) if words]
        
        dictionary = Dictionary(tokenized_docs)
        
        try:
            coherence_model = CoherenceModel(
                topics=topics_words, 
                texts=tokenized_docs, 
                dictionary=dictionary, 
                coherence='c_v'
            )
            return coherence_model.get_coherence()
        except Exception as e:
            print(f"Coherence calc error: {e}")
            return 0.0

    def export_top_words_barchart(self, output_path, n_top_words=10):
        if self.topic_model is None or not self.topic_model.get_topics(): return
        print("Generating Top Words Bar Chart...")
        valid_topics = [t for t in self.topic_model.get_topics().keys() if t != -1]
        n_topics = len(valid_topics)
        if n_topics == 0: return

        cols = 3 
        rows = int(np.ceil(n_topics / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), sharex=False)
        if not isinstance(axes, np.ndarray): axes = [axes]
        else: axes = axes.flatten()
        
        for idx, t_idx in enumerate(valid_topics):
            topic_data = self.topic_model.get_topic(t_idx)
            top_features = [word for word, _ in topic_data[:n_top_words]]
            weights = [score for _, score in topic_data[:n_top_words]]
            ax = axes[idx]
            ax.barh(top_features, weights, align='center', color='mediumpurple')
            ax.invert_yaxis() 
            ax.set_title(f'Topic {t_idx}', fontdict={'fontsize': 14, 'fontweight': 'bold'})
            ax.tick_params(axis='both', which='major', labelsize=10)
        
        for i in range(n_topics, len(axes)): fig.delaxes(axes[i])
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()

    def export_document_scatter(self, output_path, cluster_ids, n_top_words_for_legend=5):
        if self.probs is None: return
        print("Running UMAP for 2D visualization (This might take a moment)...")
        reducer = umap_learn.UMAP(n_components=2, random_state=42, metric='cosine')
        embedding = reducer.fit_transform(self.probs)
        
        unique_clusters = set(cluster_ids)
        cluster_legend_map = {}
        
        for t_idx in unique_clusters:
            if t_idx == -1:
                cluster_legend_map[t_idx] = "Topic -1: Outliers / Noise"
            else:
                topic_data = self.topic_model.get_topic(t_idx)
                if topic_data:
                    top_features = [word for word, _ in topic_data[:n_top_words_for_legend]]
                    keyword_str = ", ".join(top_features)
                    cluster_legend_map[t_idx] = f"Topic {t_idx}: {keyword_str}"
                else:
                    cluster_legend_map[t_idx] = f"Topic {t_idx}: Unknown"
            
        legend_labels = [cluster_legend_map[cid] for cid in cluster_ids]
        hue_order = [cluster_legend_map[i] for i in sorted(list(unique_clusters))]

        df = pd.DataFrame({'UMAP_1': embedding[:, 0], 'UMAP_2': embedding[:, 1], 'Cluster Focus': legend_labels})
        
        plt.figure(figsize=(15, 8)) 
        sns.scatterplot(
            data=df, x='UMAP_1', y='UMAP_2', hue='Cluster Focus', hue_order=hue_order,
            palette='tab20', alpha=0.8, s=40, edgecolor='w', linewidth=0.5
        )
        
        plt.title('BERTopic Document Clusters (UMAP 2D Projection)', fontsize=16, fontweight='bold')
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., fontsize=10)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def export_bertopic_html(self, output_prefix):
        if self.topic_model is None: return
        print("Exporting BERTopic interactive HTMLs...")
        try:
            valid_topics = [t for t in self.topic_model.get_topics().keys() if t != -1]
            n_valid_topics = len(valid_topics)

            if n_valid_topics >= 3:
                fig_topics = self.topic_model.visualize_topics()
                fig_topics.write_html(f"{output_prefix}_distance.html")
            else:
                print(f"Warning: Found only {n_valid_topics} valid topic(s). Distance Map requires >= 3 topics. Skipping.")
            
            if n_valid_topics >= 1:
                fig_barchart = self.topic_model.visualize_barchart(top_n_topics=min(10, n_valid_topics))
                fig_barchart.write_html(f"{output_prefix}_barchart.html")
                
            if n_valid_topics >= 2:
                fig_heatmap = self.topic_model.visualize_heatmap()
                fig_heatmap.write_html(f"{output_prefix}_heatmap.html")
                fig_hierarchy = self.topic_model.visualize_hierarchy()
                fig_hierarchy.write_html(f"{output_prefix}_hierarchy.html")
                
        except Exception as e:
            print(f"Failed to export BERTopic HTMLs: {e}")