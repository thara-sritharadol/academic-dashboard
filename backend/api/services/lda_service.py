from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
import spacy # <--- ต้องใช้ Spacy
import logging
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary

logger = logging.getLogger(__name__)

class LDAService:
    def __init__(self, n_topics=10):
        self.n_topics = n_topics
        self.nlp = None
        
        #Load Spacy with same BERTopic
        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
            self._setup_stopwords()
        except OSError:
            logger.error("Spacy model 'en_core_web_sm' not found.")
            raise

        #Use CountVectorizer and Use Spacy's tokenizer
        self.vectorizer = CountVectorizer(
            tokenizer=self.spacy_tokenizer, #Custom Tokenizer
            max_df=0.95, 
            min_df=2, 
        )
        
        #LDA
        self.lda_model = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method='batch'
        )
        self.feature_names = None
        self.dtm = None

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
        #Stopwords, Punctuation, Number and Lemmatize
        return [token.lemma_.lower() for token in doc 
                if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

    def fit_transform(self, documents):
        print(f"Training LDA with {self.n_topics} topics (using Spacy preprocessing)...")
        #vectorizer use spacy_tokenizer
        self.dtm = self.vectorizer.fit_transform(documents)
        self.feature_names = self.vectorizer.get_feature_names_out()
        lda_output = self.lda_model.fit_transform(self.dtm)
        return lda_output

    def get_top_words_list(self, n_top_words=10):
        topics_words = []
        for topic in self.lda_model.components_:
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
        # เพื่อความแฟร์ เราต้อง Tokenize เอกสารใหม่ด้วย Logic เดียวกันเพื่อส่งให้ Gensim
        # (หรือจะใช้ tokenizer ของ vectorizer ก็ได้)
        print("Calculating LDA Coherence...")
        tokenized_docs = self.vectorizer.build_analyzer()(documents[0]) # check analyzer
        
        # เนื่องจาก vectorizer.build_analyzer() ใน sklearn เมื่อใช้ custom tokenizer 
        # มันจะเรียกฟังก์ชันนั้นเลย เราจึงวนลูปใช้ self.spacy_tokenizer ได้เลยเพื่อความชัวร์
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