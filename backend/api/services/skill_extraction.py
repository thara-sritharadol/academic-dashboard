import os
import json
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from api.models import ExtractedSkill

def load_skill(file_path):
    if not os.path.exists:
        raise FileNotFoundError(f"not found dataset file: {file_path}")
    
    ext = os.path.splitext(file_path)[-1].lower()
    
    if ext == ".csv":
        df = pd.read_csv(file_path)
        col_candidates = [c for c in df.columns if c.lower() in ("preferredlabel", "skill_name")]
        if not col_candidates:
            raise ValueError("not found candidates column")
        skills = df[col_candidates[0]].dropna().unique().tolist()
        
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            skills = [d.get("preferredLabel") or d.get("skill_name") for d in data if isinstance(d, dict)]
            skills = [s for s in skills if s]
        else:
            raise ValueError("json structure is not valid")

    else:
        raise ValueError("only csv or json")

    print(f"load skill {len(skills):,} record")
    return skills

class SkillExtractor:
    def __init__(self, skill_list, model_name = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.skill_list = skill_list
        self.model = SentenceTransformer(model_name)
        
        print(f"Generate embedding for {len(skill_list)} skills...")
        self.skill_embeddings = self.model.encode(skill_list, convert_to_tensor=True)
        print("Skill embedding ready.")
    
    def extract_from_text(self, paper, author_name = None, top_k = 5, save_to_db=True):
        if not paper.abstract:
            return []
        
        """
        
        text_emb = self.model.encode(paper.abstract, convert_to_tensor=True)
        cos_scores = util.cos_sim(text_emb, self.skill_embeddings)[0]
        
        """
        title = paper.title or ""
        abstract = paper.abstract or ""
        
        text_to_encode = title + self.model.tokenizer.sep_token + abstract
        
        text_emb = self.model.encode(text_to_encode, convert_to_tensor=True)
        
        cos_scores = util.cos_sim(text_emb, self.skill_embeddings)[0]
        
        
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
                    embedding_model=self.model_name
                )
        return sorted(extracted, key=lambda x: x["confidence"], reverse=True)
    