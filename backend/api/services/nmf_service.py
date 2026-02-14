from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import numpy as np
import spacy
import logging
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary

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

        #Setup Vectorizer (TF-IDF)
        self.vectorizer = TfidfVectorizer(
            tokenizer=self.spacy_tokenizer, 
            max_df=0.95, 
            min_df=2
        )
        
        #Setup NMF Model
        self.nmf_model = NMF(
            n_components=n_topics,
            random_state=42,
            init='nndsvd', # Initialization for Text
            max_iter=500
        )
        self.feature_names = None
        self.doc_topic_matrix = None

    def _setup_stopwords(self):
        """Use same stopwords as BERTopic"""
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
        """Use same tokenizer logic as BERTopic"""
        if not text: return []
        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc 
                if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

    def fit_transform(self, documents):
        """Train NMF"""
        print(f"Training NMF with {self.n_topics} topics...")
        #TF-IDF Matrix
        tfidf_matrix = self.vectorizer.fit_transform(documents)
        self.feature_names = self.vectorizer.get_feature_names_out()
        
        #W matrix
        self.doc_topic_matrix = self.nmf_model.fit_transform(tfidf_matrix)
        return self.doc_topic_matrix

    def get_top_words_list(self, n_top_words=10):
        topics_words = []
        #NMF stores the Topic-Word matrix in `components_`.
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
        #Tokennize again and sent it to Gensim.
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