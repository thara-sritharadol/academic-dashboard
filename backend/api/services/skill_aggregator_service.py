#NOT USE!!!
import json
import numpy as np
import torch
from collections import Counter
from sentence_transformers import SentenceTransformer, util
from api.models import SkillEmbedding

class SkillAggregator:
    
    def __init__(self, model_name: str, l1_source: str, hierarchy_map_path: str, level_map_path: str):
        self.stdout = lambda x: print(x)
        self.model_name = model_name

        #Load model (for Pass 1)
        self.stdout(f"Loading '{model_name}'model ...")
        self.model = SentenceTransformer(model_name)
        
        #Load Embeddings (L0-L1) (for Pass 1)
        self.l1_skill_list, self.l1_skill_embeddings = self._load_skill_embeddings(l1_source)
        
        #Load Maps (for Pass 2)
        self.stdout(f"Loading Hierarchy Map from '{hierarchy_map_path}'...")
        self.hierarchy_map = self._load_json_map(hierarchy_map_path)
        
        self.stdout(f"Loading Level Map from '{level_map_path}'...")
        self.level_map = self._load_json_map(level_map_path)
        
        self.stdout("Aggregator ready to use\n")

    def _load_json_map(self, file_path: str):
        """Load JSON Map"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValueError(f"Not Found Map at: {file_path}")

    def _load_skill_embeddings(self, source: str):
        """Load L0-L1 Embeddings from DB"""
        self.stdout(f"Loading L0-L1 Embeddings (source='{source}')...")
        
        skills = SkillEmbedding.objects.filter(model_name=self.model_name, source=source)
        
        if not skills.exists():
            raise ValueError(f"Not found L0-L1 Embeddings (source='{source}', model='{self.model_name}')")
            
        skill_list = [t.skill_name for t in skills]
        emb_list = [np.frombuffer(t.embedding, dtype=np.float32) for t in skills]
        
        skill_embeddings_tensor = torch.tensor(np.vstack(emb_list), device=self.model.device)
        
        self.stdout(f"Load L0-L1 successfully {len(skill_list):,} skills.")
        return skill_list, skill_embeddings_tensor

    def get_allowed_list(self, text: str, relative_threshold=0.85, min_absolute=0.30, min_k=5):
        if not text:
            return set()
            
        text_emb = self.model.encode(text, convert_to_tensor=True, normalize_embeddings=True)
        cos_scores = util.cos_sim(text_emb, self.l1_skill_embeddings)[0]
        
        # 1. หาคะแนนสูงสุด
        max_score = torch.max(cos_scores).item()
        
        # 2. คำนวณ Dynamic Threshold
        threshold = max(max_score * relative_threshold, min_absolute)
        
        # 3. เลือก Indices ที่ผ่านเกณฑ์
        indices = torch.where(cos_scores >= threshold)[0]
        
        # ถ้าจำนวนที่ผ่านเกณฑ์ น้อยกว่า min_k (เช่น น้อยกว่า 5 อัน)
        # ให้บังคับเอา Top-5 แทน เพื่อป้องกัน Allowed List ว่างเปล่า
        if len(indices) < min_k:
            # เอา Top-K
            top_results = torch.topk(cos_scores, k=min_k)
            indices = top_results.indices
            
        #แปลงเป็น numpy array เพื่อวนลูป
        indices = indices.cpu().numpy()
        
        allowed_list = set()
        for idx in indices:
            allowed_list.add(self.l1_skill_list[idx])
            
        return allowed_list

    def get_filtered_votes(self, 
                           sub_skills, 
                           allowed_list: set, 
                           max_ancestor_level=2, 
                           min_vote_count=2,
                           min_level_to_save=1):
        
        gate_list = set(allowed_list)
        
        for skill_name in allowed_list:
            l0_skill = self.find_level_0_skill(skill_name)
            if l0_skill:
                gate_list.add(l0_skill)
        
        all_ancestors = []
        for sub_skill in sub_skills:
            ancestors_names = self.hierarchy_map.get(sub_skill.skill_name, [])
            
            for ancestor_name in ancestors_names:
                ancestor_level = self.level_map.get(ancestor_name, 99)
                if ancestor_level <= max_ancestor_level:
                    all_ancestors.append(ancestor_name)
                    
        if not all_ancestors:
            return {}

        vote_counts = Counter(all_ancestors)
        
        final_votes = {}
        
        for voted_skill, votes in vote_counts.items():
            
            if votes < min_vote_count:
                continue
                
            voted_level = self.level_map.get(voted_skill, 99)
            if voted_level < min_level_to_save:
                continue
            
            is_relevant = False
            if voted_skill in gate_list:
                is_relevant = True
            else:
                ancestors = self.hierarchy_map.get(voted_skill, [])
                for ancestor in ancestors:
                    if ancestor in gate_list:
                        is_relevant = True
                        break
            
            if not is_relevant:
                continue
                
            final_votes[voted_skill] = votes
            
        return final_votes

    def find_level_0_skill(self, skill_name: str):
        """
        Finds the Skill Level 0 of the specified skill_name.
        """
        if not skill_name:
            return None
            
        level = self.level_map.get(skill_name)
        
        if level == 0:
            return skill_name
            
        if level is None or level > 0:
            ancestors = self.hierarchy_map.get(skill_name, [])
            for ancestor_name in ancestors:
                if self.level_map.get(ancestor_name) == 0:
                    return ancestor_name
        
        return None