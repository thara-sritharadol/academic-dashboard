import pandas as pd
import spacy
from django.core.management.base import BaseCommand
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
import gensim.corpora as corpora
from gensim.models.coherencemodel import CoherenceModel
import numpy as np

# Import Model จาก App ของคุณ
from api.models import Paper

class Command(BaseCommand):
    help = 'Train BERTopic and Calculate Coherence Score (c_v)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting Evaluation Process...'))

        # ==========================================
        # 1. โหลดข้อมูลและ Preprocessing
        # ==========================================
        print("Loading Spacy and Data...")
        try:
            nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
        except OSError:
            self.stdout.write(self.style.ERROR("Error: Spacy model not found."))
            return

        # ดึงข้อมูลจาก Database
        papers_qs = Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact='')
        if not papers_qs.exists():
            self.stdout.write(self.style.ERROR("No data found."))
            return

        # แปลงเป็น List
        abstracts = list(papers_qs.values_list('abstract', flat=True))
        print(f"Loaded {len(abstracts)} papers.")

        # Stopwords
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

        def spacy_tokenizer(text):
            if not text: return []
            doc = nlp(text)
            return [token.lemma_.lower() for token in doc 
                    if not token.is_stop and not token.is_punct and not token.like_num and len(token) > 2]

        # ==========================================
        # 2. สร้างและเทรนโมเดลใหม่ (เพื่อการวัดผล)
        # ==========================================
        print("Training BERTopic for Evaluation...")
        
        # ใช้ Config เดียวกับตัวจริง
        vectorizer_model = CountVectorizer(tokenizer=spacy_tokenizer, ngram_range=(1, 2))
        umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine', random_state=42, low_memory=True)

        topic_model = BERTopic(
            umap_model=umap_model,
            min_topic_size=5,
            embedding_model="allenai/specter", 
            vectorizer_model=vectorizer_model,
            calculate_probabilities=False, 
            verbose=True
        )

        # Fit model เพื่อให้ได้ Topic info
        topic_model.fit(abstracts)

        # ==========================================
        # 3. เตรียมข้อมูลสำหรับ Gensim Coherence
        # ==========================================
        print("\nPreparing Gensim dictionary...")
        
        # เราต้อง Tokenize ข้อมูลดิบใหม่ให้เหมือนที่ BERTopic เห็น
        # โดยใช้ Analyzer จาก Vectorizer ของตัวโมเดลเอง
        vectorizer = topic_model.vectorizer_model
        analyzer = vectorizer.build_analyzer()
        
        # Tokenize เอกสารทั้งหมด
        tokens = [analyzer(doc) for doc in abstracts]

        # สร้าง Dictionary
        id2word = corpora.Dictionary(tokens)

        # ดึงคำศัพท์ในแต่ละหัวข้อ
        topic_words = []
        topic_ids = []
        topic_info = topic_model.get_topic_info()

        # วนลูปดึงเฉพาะ Topic จริง (ไม่เอา -1)
        for topic in topic_info['Topic']:
            if topic != -1:
                # ดึง Top 10 words ของแต่ละ Topic
                words = [word for word, _ in topic_model.get_topic(topic)][:10]
                topic_words.append(words)
                topic_ids.append(topic)

        if not topic_words:
            self.stdout.write(self.style.ERROR("No topics found (excluding outliers)."))
            return

        # ==========================================
        # 4. คำนวณ Coherence Score (c_v)
        # ==========================================
        print("Calculating Coherence Score (This might take a moment)...")

        # 4.1 คำนวณภาพรวม (Mean)
        coherence_model = CoherenceModel(
            topics=topic_words,
            texts=tokens,
            dictionary=id2word,
            coherence='c_v'
        )
        mean_cv = coherence_model.get_coherence()

        # 4.2 คำนวณรายหัวข้อ
        per_topic_scores = []
        # ใช้ Loop คำนวณทีละหัวข้อเพื่อความชัวร์ (Gensim บางเวอร์ชันไม่มี get_coherence_per_topic)
        for words in topic_words:
            cm = CoherenceModel(
                topics=[words],
                texts=tokens,
                dictionary=id2word,
                coherence='c_v'
            )
            try:
                per_topic_scores.append(cm.get_coherence())
            except Exception:
                per_topic_scores.append(0.0)

        # ==========================================
        # 5. แสดงผลลัพธ์
        # ==========================================
        results_df = pd.DataFrame({
            'Topic_ID': topic_ids,
            'Coherence_Cv': per_topic_scores
        })

        # Map ชื่อหัวข้อ (Label)
        # ใช้ logic ง่ายๆ เพื่อ map ชื่อ
        results_df['Name'] = results_df['Topic_ID'].apply(
            lambda x: topic_info[topic_info['Topic'] == x]['Name'].values[0]
        )

        print("\n" + "="*60)
        print(f"Overall Mean Coherence (c_v): {mean_cv:.4f}")
        print("="*60)
        
        print("\nTopics ranked by Coherence (Lowest first - Needs improvement):")
        # เรียงจากน้อยไปมาก
        print(results_df.sort_values('Coherence_Cv').to_string(index=False))

        print("\n" + "="*60)
        print("INTERPRETATION:")
        print("0.3 - 0.4 : Low coherence (Topics might be mixed)")
        print("0.4 - 0.5 : Moderate coherence")
        print("> 0.5     : Good coherence")