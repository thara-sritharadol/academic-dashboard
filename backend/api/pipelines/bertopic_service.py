import logging
import numpy as np
import spacy
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
from umap import UMAP
from bertopic import BERTopic

logger = logging.getLogger(__name__)

class BERTopicService:

    def __init__(self, n_topics=None, use_approx_dist=True, use_lemmatized_input=False):
        self.n_topics = n_topics
        self.use_approx_dist = use_approx_dist
        self.use_lemmatized_input = use_lemmatized_input
        self.nlp = None
        self.topic_model = None
        self.topics = None
        self.probs = None

        try:
            self.nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
            self.nlp.max_length = 10000000
        except OSError:
            print("Spacy model 'en_core_web_sm' not found.")
            raise

        self.academic_stopwords = [
            'finding', 'findings', 'illustrate', 'significant', 'provide', 'provides', 'potential', 'associated', 'effective', 'aspect', 'aspects', 'challenge', 'challenges',
            'paper', 'study', 'research', 'result', 'results', 'method', 'methodology',
            'proposed', 'propose', 'approach', 'based', 'using', 'used', 'use', 'to', 'we', 'source',
            'analysis', 'model', 'system', 'data', 'application', 'new', 'development',
            'performance', 'conclusion', 'abstract', 'introduction', 'work', 'time',
            'significant', 'shown', 'show', 'demonstrate', 'experiment', 'experimental',
            'university', 'department', 'author', 'et', 'al', 'figure', 'table',
            'high', 'low', 'large', 'small', 'different', 'various', 'property', 'properties', 'increase', 'effect', 'activity',
            'structure', 'compound', 'condition', 'quality', 'entry', 'contain', 'parameter', 'observe', 'report', 'present', 'evaluate'
        ]
        
        self.custom_stopwords = list(set(list(ENGLISH_STOP_WORDS) + self.academic_stopwords))

        self.vectorizer_model = CountVectorizer(
            stop_words=self.custom_stopwords, 
            ngram_range=(1, 2),
        )

    def spacy_tokenizer(self, text):
        if not text: return []
        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc 
                if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

    def fit_transform(self, documents):
        print(f"Training BERTopic (Target Topics: {self.n_topics if self.n_topics else 'Auto'})...")
        
        if self.use_approx_dist:
            print("Mode: approximate_distribution (c-TF-IDF for Soft Clustering)")
        else:
            print("Mode: calculate_probabilities (HDBSCAN for Confidence Score)")

        # Decide what kind of message to send to Model.
        if self.use_lemmatized_input:
            print("Input: Lemmatized Text (Applying Spacy preprocessing before embedding)...")
            train_docs = []
            for doc in documents:
                # Extract the words into a list, then connect them back into sentences using spaces.
                tokens = self.spacy_tokenizer(doc)
                train_docs.append(" ".join(tokens))
        else:
            print("Input: Raw Text (Default for Specter 2)")
            train_docs = documents

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
            calculate_probabilities=not self.use_approx_dist,
            nr_topics=self.n_topics if self.n_topics else None,
            verbose=True,
            top_n_words=15
        )

        # Use train_docs instead of documents.
        self.topics, self.probs = self.topic_model.fit_transform(train_docs)

        print("Reducing outliers using Embeddings strategy...")

        if -1 in self.topics:
            outliers_count = self.topics.count(-1)
            print(f"Found {outliers_count} outliers. Reducing using Embeddings strategy...")
    
            try: 
                new_topics = self.topic_model.reduce_outliers(train_docs, self.topics, strategy="embeddings", threshold=0.5)
            except Exception as e:
                print(f"Warning: Failed to reduce outliers due to {e}. Using original topics.")
                new_topics = self.topics

        else:
            print("No outliers to reduce.")
            new_topics = self.topics

        self.topic_model.update_topics(train_docs, topics=new_topics, vectorizer_model=self.vectorizer_model)
        self.topics = new_topics

        if self.use_approx_dist:
            print("Calculating approximate topic distributions (c-TF-IDF)...")
            topic_distr, _ = self.topic_model.approximate_distribution(
                train_docs, # Use `train_docs` to find the distribution, including values ​​that may or may not pass Lemma.
                min_similarity=0.01
            )
            
            row_sums = topic_distr.sum(axis=1)
            row_sums[row_sums == 0] = 1 
            topic_distr = topic_distr / row_sums[:, np.newaxis]
            
            self.probs = topic_distr

        return self.topics, self.probs

    def get_top_words_list(self, n_top_words=15):
        topics_words = []
        n_valid_topics = len(self.probs[0]) if self.probs is not None and len(self.probs) > 0 else 0
        
        for t_id in range(n_valid_topics):
            if t_id in self.topic_model.get_topics():
                words = [word for word, _ in self.topic_model.get_topic(t_id)[:n_top_words]]
                topics_words.append(words)
            else:
                topics_words.append([])
        return topics_words