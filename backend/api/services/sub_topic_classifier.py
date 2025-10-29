import time
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from nltk.tokenize import sent_tokenize
import nltk

from api.models import Paper, TopicEmbedding, ClassifiedSubTopic

class SubTopicClassifier:
    
    def __init__(self, model_name: str, source: str):
        self.stdout = lambda x: print(x) # สำหรับ logging ง่ายๆ
        
        self.stdout(f"NLTK: กำลังโหลด 'punkt' tokenizer...")
        nltk.download('punkt', quiet=True)
        
        self.stdout(f"🚀 กำลังโหลดโมเดล '{model_name}' ...")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        
        # 1. โหลด Topic Embeddings จาก Database
        self.topic_list, self.topic_embeddings = self._load_topic_embeddings(model_name, source)

    def _load_topic_embeddings(self, model_name: str, source: str):
        """
        โหลด Topic Embeddings ทั้งหมดที่ตรงกับ source และ model
        """
        self.stdout(f"📦 กำลังโหลด Topic Embeddings จาก DB (source='{source}', model='{model_name}')...")
        
        topics = TopicEmbedding.objects.filter(model_name=model_name, source=source)
        
        if not topics.exists():
            raise ValueError(f"ไม่พบ TopicEmbedding สำหรับ (source='{source}', model='{model_name}')")
            
        # ดึงข้อมูลออกมาเป็น list
        topic_list = [t.topic_name for t in topics]
        emb_list = [np.frombuffer(t.embedding, dtype=np.float32) for t in topics]
        
        # Stack เป็น
        topic_embeddings_tensor = torch.tensor(np.vstack(emb_list), device=self.model.device)
        
        self.stdout(f"✅ โหลดสำเร็จ {len(topic_list):,} topics.\n")
        return topic_list, topic_embeddings_tensor

    def classify_paper_sentences(self, paper: Paper, confidence_threshold=0.45):
        """
        ประมวลผล Paper 1 ฉบับ:
        1. แบ่งประโยค
        2. Classify ทุกประโยคเทียบกับทุก Topic
        3. กรองด้วย Threshold
        4. บันทึก "หลักฐาน" (Sub-Topics) ลง Database
        """
        
        # 1. เตรียมข้อความและแบ่งประโยค
        title = paper.title.strip() if paper.title else ""
        abstract = paper.abstract.strip() if paper.abstract else ""
        
        full_text = f"{title}. {abstract}".strip()
        
        if not full_text:
            return 0

        sentences = sent_tokenize(full_text)
        
        if not sentences:
            return 0
            
        # 2. Encode ประโยคทั้งหมดในครั้งเดียว (เร็ว)
        sentence_embs = self.model.encode(
            sentences, 
            convert_to_tensor=True, 
            normalize_embeddings=True,
            show_progress_bar=False # ปิด, เพราะเราจะใช้ tqdm ข้างนอก
        )
        
        # 3. (Optimized) คำนวณ Similarity Matrix (เร็วมาก)
        # ผลลัพธ์ที่ได้คือ Matrix ขนาด [จำนวนประโยค x จำนวน Topics]
        cos_matrix = util.cos_sim(sentence_embs, self.topic_embeddings)
        
        # 4. หาค่าสูงสุด (Top-1) ของแต่ละประโยค
        # top_results.values คือ [score], top_results.indices คือ [index]
        top_results = torch.topk(cos_matrix, k=1, dim=1)
        
        top_scores = top_results.values.cpu().numpy()[:, 0]
        top_indices = top_results.indices.cpu().numpy()[:, 0]

        # 5. เตรียมบันทึกลง Database
        objs_to_create = []
        for i, sentence in enumerate(sentences):
            score = float(top_scores[i])
            
            # --- 🛡️ การกรอง Noise ด่านที่ 1 ---
            # กรอง Sub-Topic ที่ไม่มั่นใจ (คะแนนต่ำ) ทิ้งไป
            if score < confidence_threshold:
                continue
                
            topic_index = top_indices[i]
            topic_name = self.topic_list[topic_index]
            
            objs_to_create.append(
                ClassifiedSubTopic(
                    paper=paper,
                    topic_name=topic_name,
                    confidence=score,
                    source_sentence=sentence,
                    embedding_model=self.model_name
                )
            )
            
        # 6. บันทึก "หลักฐาน" ทั้งหมดลง DB
        if objs_to_create:
            ClassifiedSubTopic.objects.bulk_create(objs_to_create, ignore_conflicts=True)
            
        return len(objs_to_create)