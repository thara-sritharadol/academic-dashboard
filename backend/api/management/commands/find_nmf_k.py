import os
import json
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import spacy
from gensim.corpora.dictionary import Dictionary
from gensim.models.coherencemodel import CoherenceModel

class Command(BaseCommand):
    help = "Find optimal K for NMF using Reconstruction Error and Topic Coherence with Spacy Preprocessing."

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, required=True, help='Path to the JSON dataset file')
        parser.add_argument('--start_k', type=int, default=2, help='Starting value for K (min 2)')
        parser.add_argument('--end_k', type=int, default=30, help='Ending value for K')
        parser.add_argument('--step_k', type=int, default=2, help='Step size for K')
        parser.add_argument('--output_dir', type=str, default='.', help='Directory to save the plot')

    def handle(self, *args, **options):
        input_file = options['input']
        start_k = max(2, options['start_k'])
        end_k = options['end_k']
        step_k = options['step_k']
        output_dir = options['output_dir']

        if not os.path.exists(input_file):
            raise CommandError(f"File '{input_file}' does not exist.")

        self.stdout.write(self.style.NOTICE(f"Loading data from {input_file}..."))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        texts = [item.get('text', '') for item in data if item.get('text', '').strip()]

        if not texts:
            raise CommandError("No text data found in the dataset.")

        # Set up Spacy and Custom Stop Words ---
        self.stdout.write("Loading Spacy 'en_core_web_sm'...")
        try:
            nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
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
                nlp.vocab[word].is_stop = True
        except OSError:
            raise CommandError("Spacy model not found. Run: python -m spacy download en_core_web_sm")

        def spacy_tokenizer(text):
            if not text: return []
            doc = nlp(text)
            return [token.lemma_.lower() for token in doc 
                    if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(texts)} papers. Preparing TF-IDF Vectorizer with Spacy..."))

        # Prepare data for NMF (using TfidfVectorizer + Spacy)
        vectorizer = TfidfVectorizer(tokenizer=spacy_tokenizer, max_df=0.90, min_df=5)
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        # Coherence (Gensim)
        self.stdout.write("Tokenizing texts for Gensim Coherence Model using Spacy...")
        tokenized_texts = [spacy_tokenizer(text) for text in texts]
        dictionary = Dictionary(tokenized_texts)

        k_values = list(range(start_k, end_k + 1, step_k))
        reconstruction_errors = []
        coherence_scores = []

        self.stdout.write(self.style.NOTICE(f"Starting Grid Search for NMF (K={start_k} to {end_k})..."))

        # Loop to find the value of K ---
        with tqdm(total=len(k_values), desc="Tuning NMF", dynamic_ncols=True) as pbar:
            for k in k_values:
                nmf_model = NMF(n_components=k, random_state=42, max_iter=500)
                nmf_model.fit(tfidf_matrix)
                
                # Reconstruction Error
                reconstruction_errors.append(nmf_model.reconstruction_err_)

                # Top 10 words
                top_words_per_topic = []
                for topic in nmf_model.components_:
                    top_features_ind = topic.argsort()[: -10 - 1 : -1]
                    top_words_per_topic.append([feature_names[i] for i in top_features_ind])

                cm = CoherenceModel(
                    topics=top_words_per_topic, 
                    texts=tokenized_texts, 
                    dictionary=dictionary, 
                    coherence='c_v'
                )
                coherence_scores.append(cm.get_coherence())
                
                pbar.update(1)

        # Dual-axis
        fig, ax1 = plt.subplots(figsize=(10, 6))

        color = 'tab:red'
        ax1.set_xlabel('Number of Topics (K)')
        ax1.set_ylabel('Reconstruction Error', color=color)
        ax1.plot(k_values, reconstruction_errors, marker='x', color=color, linestyle='--', linewidth=2, label='Reconstruction Error')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_xticks(k_values)
        ax1.grid(True, linestyle=':', alpha=0.6)

        ax2 = ax1.twinx()  
        color = 'tab:blue'
        ax2.set_ylabel('Topic Coherence ($C_v$)', color=color)
        ax2.plot(k_values, coherence_scores, marker='o', color=color, linewidth=2, label='Topic Coherence')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title('Optimal K Selection for NMF (Spacy Preprocessed)\n(Reconstruction Error vs Topic Coherence)')
        fig.tight_layout()

        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='center right')
        
        filename = "nmf_optimal_k_selection.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300)
        plt.close()

        self.stdout.write(self.style.SUCCESS(f"\nDone! Plot saved to {output_path}"))