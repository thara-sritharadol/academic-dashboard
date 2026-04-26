import os
import json
import boto3
from datetime import datetime
from tqdm import tqdm
import spacy
import numpy as np
from bertopic import BERTopic
from umap import UMAP
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
from hdbscan import HDBSCAN
import google.generativeai as genai
from collections import Counter

class BERTopicService:
    def __init__(self, n_topics=None, use_approx_dist=False, use_lemmatized_input=False):
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

        if self.use_lemmatized_input:
            print("Input: Lemmatized Text (Applying Spacy preprocessing before embedding)...")
            train_docs = []
            for doc in documents:
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

        self.topics, self.probs = self.topic_model.fit_transform(train_docs)

        print("Reducing outliers using Embeddings strategy...")
        new_topics = self.topic_model.reduce_outliers(train_docs, self.topics, strategy="embeddings", threshold=0.5)

        self.topic_model.update_topics(train_docs, topics=new_topics, vectorizer_model=self.vectorizer_model)
        self.topics = new_topics

        if self.use_approx_dist:
            print("Calculating approximate topic distributions (c-TF-IDF)...")
            topic_distr, _ = self.topic_model.approximate_distribution(
                train_docs,
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

    def calculate_topic_diversity(self, n_top_words=15):
        topics_words = self.get_top_words_list(n_top_words)
        unique_words = set()
        total_words = 0
        for topic in topics_words:
            if not topic: continue
            unique_words.update(topic)
            total_words += len(topic)
        if total_words == 0: return 0
        return len(unique_words) / total_words

def tune_thresholds(papers_data_raw, topics, probs, target_level=0, score_threshold=0.3):
    print("\n[Auto-Tune] Running Grid Search to find optimal thresholds...")
    y_true_dominant = []
    papers_eval_data = []

    # เตรียมข้อมูล Ground Truth
    for item in papers_data_raw:
        true_labels_set = set()
        top_label = None

        concepts = item.get('concepts', [])
        if isinstance(concepts, str):
            try:
                concepts = json.loads(concepts)
            except:
                concepts = []

        valid_concepts = []
        for c in concepts:
            if c.get('level') == target_level and c.get('score', 0) >= score_threshold:
                true_labels_set.add(c['display_name'])
                valid_concepts.append(c)

        if valid_concepts:
            valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
            top_label = valid_concepts[0]['display_name']

        y_true_dominant.append(top_label)
        papers_eval_data.append({'true_labels': list(true_labels_set)})

    has_ground_truth = any(len(p['true_labels']) > 0 for p in papers_eval_data)
    if not has_ground_truth:
        print("No Ground Truth found in data. Using default thresholds (Abs=0.10, Rel=0.10).")
        return 0.10, 0.10

    # สร้าง Mapping คลัสเตอร์กับ Label
    cluster_to_label_map = {}
    unique_clusters = set(topics)
    for cid in unique_clusters:
        indices = [i for i, x in enumerate(topics) if x == cid]
        if indices:
            labels_in_cluster = [y_true_dominant[i] for i in indices if y_true_dominant[i] is not None]
            if labels_in_cluster:
                cluster_to_label_map[cid] = Counter(labels_in_cluster).most_common(1)[0][0]
            else:
                cluster_to_label_map[cid] = 'Unknown'
        else:
            cluster_to_label_map[cid] = 'Unknown'

    # เริ่มรันหาค่าที่ดีที่สุด
    abs_thresholds = np.round(np.arange(0.05, 0.26, 0.05), 2)
    rel_thresholds = np.round(np.arange(0.1, 0.6, 0.1), 2)

    best_f1 = 0.0
    best_params = (0.10, 0.10)

    for abs_t in abs_thresholds:
        for rel_t in rel_thresholds:
            f1_list = []
            for doc_idx, paper_item in enumerate(papers_eval_data):
                true_labels_set = set(paper_item['true_labels'])
                if not true_labels_set: continue

                pred_labels = set()
                paper_probs = probs[doc_idx]
                max_prob = max(paper_probs) if len(paper_probs) > 0 else 0

                for t_id, prob in enumerate(paper_probs):
                    if prob > abs_t and prob >= (max_prob * rel_t):
                        mapped_label = cluster_to_label_map.get(t_id, 'Unknown')
                        if mapped_label != 'Unknown':
                            pred_labels.add(mapped_label)

                hard_cluster_id = int(topics[doc_idx])
                if not pred_labels:
                    pred_labels.add(cluster_to_label_map.get(hard_cluster_id, 'Unknown'))

                intersection = len(true_labels_set & pred_labels)
                p = intersection / len(pred_labels) if pred_labels else 0
                r = intersection / len(true_labels_set) if true_labels_set else 0
                f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
                f1_list.append(f1)

            avg_f1 = np.mean(f1_list) if f1_list else 0
            if avg_f1 > best_f1:
                best_f1 = avg_f1
                best_params = (abs_t, rel_t)

    print(f"Optimal Thresholds Found: Abs = {best_params[0]:.2f}, Rel = {best_params[1]:.2f} (Best F1: {best_f1:.4f})")
    return best_params[0], best_params[1]

# ── 2. ฟังก์ชันเรียก Gemini ตั้งชื่อ ──
def generate_llm_names(topic_model, api_key):
    if not api_key:
        print("No Gemini API key provided. Falling back to default keywords.")
        return {}

    print("\nCalling Gemini LLM to generate topic names...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest') # อัปเดตชื่อโมเดลเป็นตัวล่าสุด

    topic_info = topic_model.get_topic_info()
    prompt = (
        "You are an expert academic researcher and librarian. "
        "I have a list of topics generated by a topic modeling algorithm from research papers. "
        "For each topic, I will provide the top 15 keywords\n"
        "Your task is to create a concise, professional academic category name (2-5 words) for each topic. "
        "Respond ONLY with a valid JSON format mapping the Topic ID (string) to the generated name.\n"
        "Example: {\"0\": \"Clinical Stroke Management\", \"1\": \"Quantum Computing Algorithms\"}\n\n"
    )

    for _, row in topic_info.iterrows():
        topic_id = row['Topic']
        if topic_id == -1: continue

        keywords = [word for word, _ in topic_model.get_topic(topic_id)][:15]
        prompt += f"Topic ID: {topic_id}\n"
        prompt += f"Keywords: {', '.join(keywords)}\n"

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        llm_mapping = json.loads(response.text)
        print("LLM successfully generated topic names!")
        return llm_mapping
    except Exception as e:
        print(f"Failed to parse LLM response: {e}")
        return {}

def main():
    # 1. ตั้งค่า Environment และ Path
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Path สำหรับ Input (Deduplicated Data)
    dedupe_file_path = f"local_data/dedupe-zone/{date_str}/deduplicated_papers.json"
    
    # Path สำหรับ Output (Results Zone)
    results_folder = f"local_data/results-zone/{date_str}"
    results_file_path = f"{results_folder}/bertopic_results.json"
    
    s3_results_key = f"results-zone/{date_str}/bertopic_results.json"
    s3_latest_key = "results-zone/bertopic_results_latest.json"

    if not os.path.exists(dedupe_file_path):
        print(f"Error: ไม่พบไฟล์ Input ที่ {dedupe_file_path}")
        return

    # 2. โหลดข้อมูล
    print(f"Loading deduplicated data from {dedupe_file_path}...")
    with open(dedupe_file_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    docs = []
    valid_papers = []

    # 3. เตรียมข้อมูล Text
    for p in papers:
        title = p.get('title', '') or ''
        abstract = p.get('abstract', '') or ''
        full_text = f"{title}. {abstract}".strip()

        if not full_text or len(full_text) < 10:
            continue

        docs.append(full_text)
        valid_papers.append(p) # เก็บ Object เดิมไว้เพื่อเติมข้อมูล

    print(f"Successfully loaded {len(docs)} documents.")

    # 4. เทรนโมเดล BERTopic
    # (หมายเหตุ: สเตปนี้จะกิน RAM และ CPU สูงมาก เหมาะสำหรับรันบน Fargate)
    service = BERTopicService(n_topics=None, use_approx_dist=False, use_lemmatized_input=False)
    topics, probs = service.fit_transform(docs)
    topic_model = service.topic_model

    print("BERTopic Training Completed!")

    # 5. หา Threshold และตั้งชื่อด้วย LLM
    best_abs, best_rel = tune_thresholds(valid_papers, topics, probs)
    llm_names = generate_llm_names(topic_model, gemini_api_key)

    # 6. ผสานข้อมูล Topic กลับเข้าสู่ Paper
    print("\nEnriching papers with topic labels...")
    
    for i, paper in enumerate(valid_papers):
        topic_id = topics[i]
        paper_prob = probs[i].tolist() if probs is not None else []

        if topic_id == -1:
            cluster_label = "Outlier / Noise"
            raw_keywords = []
        else:
            topic_str_id = str(topic_id)
            # ดึงคำสำคัญจาก Model
            raw_keywords = [w for w, _ in topic_model.get_topic(topic_id)][:15]
            # ใช้ชื่อจาก LLM ถ้ามี ถ้าไม่มีใช้ 5 คำแรก
            topic_name = llm_names.get(topic_str_id, ', '.join(raw_keywords[:5]))
            cluster_label = f"Topic {topic_id}: {topic_name}"

        multi_labels = [cluster_label]

        # คำนวณ Multi-labels
        if topic_id != -1 and len(paper_prob) > 0:
            max_prob = max(paper_prob)
            for alt_topic_id, prob in enumerate(paper_prob):
                if alt_topic_id != topic_id and prob > best_abs and prob >= (max_prob * best_rel):
                    alt_str_id = str(alt_topic_id)
                    alt_keywords = [w for w, _ in topic_model.get_topic(alt_topic_id)][:5]
                    alt_name = llm_names.get(alt_str_id, ', '.join(alt_keywords))
                    multi_labels.append(f"Topic {alt_topic_id}: {alt_name}")

        # เพิ่มฟิลด์ใหม่เข้าไปใน Dict ของ Paper โดยตรง
        paper["cluster_id"] = int(topic_id)
        paper["cluster_label"] = cluster_label
        paper["predicted_multi_labels"] = multi_labels
        paper["topic_keywords"] = raw_keywords
        paper["topic_distribution"] = paper_prob

    # 7. บันทึกไฟล์ผลลัพธ์ลง Local
    os.makedirs(results_folder, exist_ok=True)
    json_data = json.dumps(valid_papers, ensure_ascii=False, indent=2)
    with open(results_file_path, "w", encoding="utf-8") as f:
        f.write(json_data)
    print(f"Local results saved to: {results_file_path}")

    # 8. อัปโหลดขึ้น S3
    if bucket_name:
        print(f"Uploading final results to S3...")
        s3_client = boto3.client('s3')
        try:
            s3_client.put_object(Bucket=bucket_name, Key=s3_results_key, Body=json_data, ContentType="application/json")
            s3_client.put_object(Bucket=bucket_name, Key=s3_latest_key, Body=json_data, ContentType="application/json")
            print(f"S3 Upload Complete: {s3_results_key}")
        except Exception as e:
            print(f"S3 Upload Failed: {e}")

if __name__ == "__main__":
    main()