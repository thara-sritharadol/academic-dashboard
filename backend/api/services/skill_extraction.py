import os
import json
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from api.models import ExtractedSkill, SkillEmbedding
from nltk import sent_tokenize

# ------------------------------
# โหลดจาก DB เหมือนเดิม
# ------------------------------
def load_skills_from_db(model_name: str):
    print(f"📦 Loading skills from database for model: {model_name}")
    skills = SkillEmbedding.objects.filter(model_name=model_name)
    if not skills.exists():
        raise ValueError(f"No SkillEmbedding found for model '{model_name}'")

    skill_list = [s.skill_name for s in skills]
    emb_list = [np.frombuffer(s.embedding, dtype=np.float32) for s in skills]
    skill_embeddings = np.vstack(emb_list)
    print(f"✅ Loaded {len(skill_list):,} skills from DB.")
    return skill_list, skill_embeddings


# ------------------------------
# SkillExtractor (ปรับใหม่)
# ------------------------------
class SkillExtractor:
    def __init__(self, model_name="all-mpnet-base-v2", use_db=True, use_sentence_split=False, skill_list=None):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.use_sentence_split = use_sentence_split

        if use_db:
            self.skill_list, self.skill_embeddings = load_skills_from_db(model_name)
        else:
            if not skill_list:
                raise ValueError("skill_list must be provided when use_db=False")
            print(f"Generate embedding for {len(skill_list)} skills...")
            self.skill_list = skill_list
            self.skill_embeddings = self.model.encode(skill_list, convert_to_tensor=True)
            print("Skill embedding ready.")

    # ------------------------------------------------------------
    # การสกัดทักษะจากเอกสาร (รองรับ sentence split)
    # ------------------------------------------------------------
    def extract_from_text(self, paper, author_name=None, top_k=5, save_to_db=True):
        if not paper.abstract:
            return []

        text = paper.abstract.strip()
        if not text:
            return []

        # ✅ ถ้าเลือกใช้ Sentence Splitting
        if self.use_sentence_split:
            sentences = sent_tokenize(text)
            if len(sentences) == 0:
                sentences = [text]

            # encode ทุกประโยค
            text_embs = self.model.encode(sentences, convert_to_tensor=True)
            # คำนวณ similarity ระหว่างทุกประโยคกับทุกสกิล
            cos_matrix = util.cos_sim(text_embs, self.skill_embeddings)
            # เอาค่าความคล้ายสูงสุดของแต่ละ skill (max over sentences)
            cos_scores = cos_matrix.max(dim=0).values

        else:
            # เดิม: ใช้ทั้ง abstract
            text_emb = self.model.encode(text, convert_to_tensor=True)
            cos_scores = util.cos_sim(text_emb, self.skill_embeddings)[0]

        # หา top-k skills ที่ใกล้เคียงที่สุด
        top_results = np.argpartition(-cos_scores, range(top_k))[:top_k]
        extracted = []
        for idx in top_results:
            skill_name = self.skill_list[idx]
            confidence = float(cos_scores[idx])
            extracted.append({
                "paper_id": paper.id,
                "author_name": author_name,
                "skill_name": skill_name,
                "confidence": confidence,
                "model": self.model_name,
            })

            if save_to_db:
                ExtractedSkill.objects.create(
                    paper=paper,
                    author_name=author_name,
                    skill_name=skill_name,
                    confidence=confidence,
                    embedding_model=self.model_name,
                )

        return sorted(extracted, key=lambda x: x["confidence"], reverse=True)
