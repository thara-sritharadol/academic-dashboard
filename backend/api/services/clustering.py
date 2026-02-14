#Not Use
import sys
import re
import numpy as np
import spacy
from django.db.models import Count
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from api.models import Paper, Author

#Load SpaCy Model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Error: SpaCy model 'en_core_web_sm' not found.")
    print("Please run: python -m spacy download en_core_web_sm")
    sys.exit(1)

class ClusteringService:
    def __init__(self, n_clusters=5):
        self.n_clusters = n_clusters
        self.custom_stopwords = self._get_academic_stopwords()

    def _get_academic_stopwords(self):
        base_stops = nlp.Defaults.stop_words
        academic_stops = {
            'paper', 'study', 'research', 'proposed', 'method', 'methodology', 
            'result', 'results', 'conclusion', 'analysis', 'based', 'using', 
            'used', 'approach', 'algorithm', 'system', 'model', 'data', 'datum',
            'performance', 'application', 'new', 'development', 'technique',
            'survey', 'review', 'present', 'presents', 'show', 'shows', 
            'demonstrate', 'significant', 'experimental', 'experiment', 
            'evaluation', 'propose', 'table', 'figure', 'introduction', 
            'abstract', 'work', 'time', 'problem', 'solution', 'information',
            'university', 'department', 'faculty', 'thesis', 'project',
            'author', 'et', 'al', 'simulation', 'case', 'compare', 'comparison'
        }
        return base_stops.union(academic_stops)

    def _preprocess_abstracts(self, abstracts):
        #Use SpaCy to Clean Text
        cleaned_docs = []
        print(f"   > NLP Processing {len(abstracts)} abstracts...")
        
        #nlp.pipe
        for doc in nlp.pipe(abstracts, disable=["parser", "ner"]):
            tokens = []
            for token in doc:
                # USE NOUN, ADJ, PROPN and No Stopwords
                if (token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and 
                    token.text.lower() not in self.custom_stopwords and
                    token.lemma_.lower() not in self.custom_stopwords and
                    token.is_alpha):
                    
                    tokens.append(token.lemma_.lower())
                    
            cleaned_docs.append(" ".join(tokens))
            
        return cleaned_docs

    def run(self):
        #Main method for Clustering
        print(f"Starting Clustering Service (K={self.n_clusters})...")
        
        #fetch
        papers = list(Paper.objects.filter(abstract__isnull=False).exclude(abstract=''))
        if len(papers) < self.n_clusters:
            print(f"Error: Not enough papers ({len(papers)}) for {self.n_clusters} clusters.")
            return

        #clean
        raw_abstracts = [p.abstract for p in papers]
        clean_abstracts = self._preprocess_abstracts(raw_abstracts)

        #Vectorization
        print("   > Vectorizing abstracts (TF-IDF)...")
        try:
            vectorizer = TfidfVectorizer(
                max_features=2000,
                max_df=0.5,
                min_df=5,
                ngram_range=(1, 2)
            )
            X = vectorizer.fit_transform(clean_abstracts)
        except ValueError as e:
            print(f"Error during vectorization: {e}")
            return

        #Group by K-Means
        print("   > Running K-Means algorithm...")
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        kmeans.fit(X)

        #Labeling
        print("   > Generating labels...")
        cluster_names = self._generate_labels(kmeans, vectorizer)

        #Save Results
        print("   > Saving results to Papers...")
        self._save_paper_results(papers, kmeans.labels_, cluster_names)
        
        #Update Authors
        print("   > Updating Author Profiles (Pre-calculating clusters)...")
        self._update_authors_primary_cluster()
        
        print("Clustering process completed successfully!")

    def _generate_labels(self, kmeans, vectorizer, top_n=5):
        terms = vectorizer.get_feature_names_out()
        ordered_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        labels = {}
        for i in range(self.n_clusters):
            top_terms = [terms[ind] for ind in ordered_centroids[i, :top_n]]
            labels[i] = ", ".join(top_terms)
            print(f"      Cluster {i}: {labels[i]}")
        return labels

    def _save_paper_results(self, papers, labels, cluster_names):
        updates = []
        for paper, label_id in zip(papers, labels):
            paper.cluster_id = int(label_id)
            paper.cluster_label = cluster_names[label_id]
            updates.append(paper)
        Paper.objects.bulk_update(updates, ['cluster_id', 'cluster_label'])
        print(f"      Updated {len(updates)} papers.")

    def _update_authors_primary_cluster(self):
        #Calculate which research cluster each professor belongs to the most and record it in the 'primary_cluster' field of the Author.
        authors = Author.objects.annotate(paper_count=Count('papers')).filter(paper_count__gt=0).prefetch_related('papers')
        
        updates = []
        for author in authors:
            clusters = [
                p.cluster_label for p in author.papers.all() 
                if p.cluster_label
            ]
            
            if not clusters:
                continue

            from collections import Counter
            most_common = Counter(clusters).most_common(1)
            
            if most_common:
                primary_cluster = most_common[0][0]
                
                if author.primary_cluster != primary_cluster:
                    author.primary_cluster = primary_cluster
                    updates.append(author)
        
        if updates:
            Author.objects.bulk_update(updates, ['primary_cluster'])
        
        print(f"      Updated primary cluster for {len(updates)} authors.")