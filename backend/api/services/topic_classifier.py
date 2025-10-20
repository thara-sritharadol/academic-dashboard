import numpy as np
from sentence_transformers import SentenceTransformer, util
# ## NEW ##: Import Model ใหม่ และเปลี่ยนชื่อ ExtractedSkill เป็น ClassifiedTopic หรืออื่นๆ
from api.models import ClassifiedTopic, TopicEmbedding
from nltk import sent_tokenize

# ## CHANGED ##: เปลี่ยนชื่อฟังก์ชันและ Model
def load_topics_from_db(model_name: str):
    print(f"📦 Loading topics from database for model: {model_name}")
    topics = TopicEmbedding.objects.filter(model_name=model_name)
    if not topics.exists():
        raise ValueError(f"No TopicEmbedding found for model '{model_name}'")

    topic_list = [t.topic_name for t in topics]
    emb_list = [np.frombuffer(t.embedding, dtype=np.float32) for t in topics]
    topic_embeddings = np.vstack(emb_list)
    print(f"✅ Loaded {len(topic_list):,} topics from DB.")
    return topic_list, topic_embeddings


# ## CHANGED ##: เปลี่ยนชื่อ Class
class TopicClassifier:
    def __init__(self, model_name="all-mpnet-base-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
        # โหลด topics จาก DB เสมอสำหรับ use case นี้
        self.topic_list, self.topic_embeddings = load_topics_from_db(model_name)

    # ## CHANGED ##: เปลี่ยนชื่อ method และ parameter เล็กน้อย
    def classify_paper(self, paper: Paper, top_k=3, confidence_threshold=0.4, save_to_db=True):
        """
        Classifies the topic for a given Paper object based on its abstract.
        """
        text = paper.abstract
        if not text or not text.strip():
            return []

        # การ encode ทั้ง abstract มักจะให้ผลดีกว่าสำหรับ Topic Classification
        text_emb = self.model.encode(text.strip(), convert_to_tensor=True, normalize_embeddings=True)
        
        # คำนวณ similarity ระหว่าง abstract กับทุก topic
        cos_scores = util.cos_sim(text_emb, self.topic_embeddings)[0]

        # หา top-k topics ที่ใกล้เคียงที่สุด
        # แก้ไขให้รองรับกรณีที่จำนวน topic ทั้งหมดน้อยกว่า top_k
        effective_top_k = min(top_k, len(self.topic_list))
        top_results = np.argpartition(-cos_scores, range(effective_top_k))[:effective_top_k]
        
        results = []
        for idx in top_results:
            topic_name = self.topic_list[idx]
            confidence = float(cos_scores[idx])
            
            # กรองผลลัพธ์ตาม confidence threshold
            if confidence >= confidence_threshold:
                results.append({
                    "topic_name": topic_name,
                    "confidence": confidence,
                })
                
                # --- ✅ NEW: ส่วนของการบันทึกลง DB ---
                if save_to_db:
                    # ใช้ update_or_create เพื่อป้องกันข้อมูลซ้ำซ้อน
                    # หากมีการ classify paper เดิมซ้ำ จะทำการอัปเดตค่า confidence
                    ClassifiedTopic.objects.update_or_create(
                        paper=paper,
                        topic_name=topic_name,
                        embedding_model=self.model_name,
                        defaults={'confidence': confidence}
                    )

        return sorted(results, key=lambda x: x["confidence"], reverse=True)