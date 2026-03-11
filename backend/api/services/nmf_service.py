from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import numpy as np
import spacy
import logging
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary
import matplotlib.pyplot as plt
import seaborn as sns
import umap
import pandas as pd
import plotly.express as px

logger = logging.getLogger(__name__)

class NMFService:
    def __init__(self, n_topics=10):
        self.n_topics = n_topics
        self.nlp = None
        
        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
            self._setup_stopwords()
        except OSError:
            logger.error("Spacy model 'en_core_web_sm' not found.")
            raise

        self.vectorizer = TfidfVectorizer(
            tokenizer=self.spacy_tokenizer, 
            max_df=0.90, 
            min_df=5,
            ngram_range=(1, 2)
        )
        
        self.nmf_model = NMF(
            n_components=n_topics,
            random_state=42,
            init='nndsvd',
            max_iter=500
        )
        self.feature_names = None
        self.doc_topic_matrix = None

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
        print(f"Training NMF with {self.n_topics} topics...")
        tfidf_matrix = self.vectorizer.fit_transform(documents)
        self.feature_names = self.vectorizer.get_feature_names_out()
        self.doc_topic_matrix = self.nmf_model.fit_transform(tfidf_matrix)
        return self.doc_topic_matrix

    def get_top_words_list(self, n_top_words=10):
        topics_words = []
        for topic in self.nmf_model.components_:
            top_features_ind = topic.argsort()[:-n_top_words - 1:-1]
            top_features = [self.feature_names[i] for i in top_features_ind]
            topics_words.append(top_features)
        return topics_words

    def calculate_topic_diversity(self, n_top_words=10):
        topics_words = self.get_top_words_list(n_top_words)
        unique_words = set()
        total_words = 0
        for topic in topics_words:
            unique_words.update(topic)
            total_words += len(topic)
        if total_words == 0: return 0
        return len(unique_words) / total_words

    def calculate_coherence_score(self, documents):
        print("Calculating NMF Coherence...")
        tokenized_docs = [self.spacy_tokenizer(doc) for doc in documents]
        topics_words = self.get_top_words_list(n_top_words=10)
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
        """สร้างกราฟแท่ง (Bar Chart) แสดงน้ำหนักของ 10 คำแรกในแต่ละ Topic"""
        if self.nmf_model is None or self.feature_names is None:
            print("Error: NMF model not trained.")
            return
            
        print("Generating Top Words Bar Chart...")
        n_topics = self.n_topics
        cols = 3 # ตั้งค่าจำนวนคอลัมน์ของกราฟย่อย
        rows = int(np.ceil(n_topics / cols))
        
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), sharex=False)
        axes = axes.flatten()
        
        for t_idx, topic in enumerate(self.nmf_model.components_):
            top_features_ind = topic.argsort()[:-n_top_words - 1:-1]
            top_features = [self.feature_names[i] for i in top_features_ind]
            weights = topic[top_features_ind]
            
            ax = axes[t_idx]
            ax.barh(top_features, weights, align='center', color='skyblue')
            ax.invert_yaxis() # ให้คำที่มีน้ำหนักมากสุดอยู่ด้านบน
            ax.set_title(f'Topic {t_idx}', fontdict={'fontsize': 14, 'fontweight': 'bold'})
            ax.tick_params(axis='both', which='major', labelsize=10)
        
        # ซ่อนกราฟช่องที่ว่างอยู่ (ถ้ามี)
        for i in range(n_topics, len(axes)):
            fig.delaxes(axes[i])
            
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()

    def export_document_scatter(self, output_path, cluster_ids, n_top_words_for_legend=5):
        """สร้างพิกัด 2 มิติ (2D Scatter Plot) ด้วย UMAP พร้อมโชว์ Keyword บน Legend"""
        if self.doc_topic_matrix is None:
            print("Error: Document topic matrix not found.")
            return
            
        print("Running UMAP for 2D visualization (This might take a moment)...")
        reducer = umap.UMAP(n_components=2, random_state=42, metric='cosine')
        embedding = reducer.fit_transform(self.doc_topic_matrix)
        
        # --- ดึง Keyword มาสร้างเป็นชื่อ Label สวยๆ ให้แต่ละกลุ่ม ---
        unique_clusters = set(cluster_ids)
        cluster_legend_map = {}
        for t_idx in unique_clusters:
            topic = self.nmf_model.components_[t_idx]
            # ดึงคำศัพท์ที่คะแนนสูงสุด 5 อันดับ
            top_features_ind = topic.argsort()[:-n_top_words_for_legend - 1:-1]
            top_features = [self.feature_names[i] for i in top_features_ind]
            keyword_str = ", ".join(top_features)
            # สร้างข้อความ เช่น "Topic 0: cell, protein, gene..."
            cluster_legend_map[t_idx] = f"Topic {t_idx}: {keyword_str}"
            
        # แมป ID ของทุกเปเปอร์ให้กลายเป็นข้อความ Keyword ยาวๆ
        legend_labels = [cluster_legend_map[cid] for cid in cluster_ids]
        
        # จัดเรียงลำดับ Topic ให้สวยงาม (0, 1, 2...)
        hue_order = [cluster_legend_map[i] for i in sorted(list(unique_clusters))]

        df = pd.DataFrame({
            'UMAP_1': embedding[:, 0],
            'UMAP_2': embedding[:, 1],
            'Cluster Focus': legend_labels # เปลี่ยนชื่อคอลัมน์ให้สื่อความหมาย
        })
        
        plt.figure(figsize=(15, 8)) # ขยายความกว้างกราฟเพื่อรองรับตัวหนังสือ Legend ที่ยาวขึ้น
        import seaborn as sns
        sns.scatterplot(
            data=df, 
            x='UMAP_1', 
            y='UMAP_2', 
            hue='Cluster Focus', 
            hue_order=hue_order,
            palette='tab10', 
            alpha=0.8, 
            s=40,
            edgecolor='w',
            linewidth=0.5
        )
        
        plt.title('NMF Document Clusters (UMAP 2D Projection)', fontsize=16, fontweight='bold')
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., fontsize=10)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def export_document_scatter_3d(self, output_path, cluster_ids, n_top_words_for_legend=5):
        """สร้างพิกัด 3 มิติ (3D Scatter Plot) ด้วย UMAP บันทึกเป็น Interactive HTML"""
        if self.doc_topic_matrix is None:
            print("Error: Document topic matrix not found.")
            return
            
        print("Running UMAP for 3D visualization (This might take a moment)...")
        reducer = umap.UMAP(n_components=3, random_state=42, metric='cosine')
        embedding = reducer.fit_transform(self.doc_topic_matrix)
        
        unique_clusters = set(cluster_ids)
        cluster_legend_map = {}
        for t_idx in unique_clusters:
            topic = self.nmf_model.components_[t_idx]
            top_features_ind = topic.argsort()[:-n_top_words_for_legend - 1:-1]
            top_features = [self.feature_names[i] for i in top_features_ind]
            keyword_str = ", ".join(top_features)
            cluster_legend_map[t_idx] = f"Topic {t_idx}: {keyword_str}"
            
        legend_labels = [cluster_legend_map[cid] for cid in cluster_ids]

        df = pd.DataFrame({
            'UMAP_1': embedding[:, 0],
            'UMAP_2': embedding[:, 1],
            'UMAP_3': embedding[:, 2],
            'Cluster Focus': legend_labels
        })
        
        fig = px.scatter_3d(
            df, x='UMAP_1', y='UMAP_2', z='UMAP_3',
            color='Cluster Focus',
            title='NMF Document Clusters (UMAP 3D Projection)',
            opacity=0.8,
            color_discrete_sequence=px.colors.qualitative.Alphabet
        )
        
        fig.update_traces(marker=dict(size=4, line=dict(width=0.5, color='white')))
        fig.update_layout(legend=dict(itemsizing='constant'))
        
        fig.write_html(output_path)
        print(f"Successfully saved 3D scatter plot to {output_path}")