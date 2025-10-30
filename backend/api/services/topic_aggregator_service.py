import json
import numpy as np
import torch
from collections import Counter
from sentence_transformers import SentenceTransformer, util
from api.models import TopicEmbedding

class TopicAggregator:
    
    def __init__(self, model_name: str, l1_source: str, hierarchy_map_path: str, level_map_path: str):
        self.stdout = lambda x: print(x)
        self.model_name = model_name

        # 1. โหลดโมเดล (สำหรับ Pass 1)
        self.stdout(f"🚀 กำลังโหลดโมเดล '{model_name}' ...")
        self.model = SentenceTransformer(model_name)
        
        # 2. โหลด Embeddings (L0-L1) (สำหรับ Pass 1)
        self.l1_topic_list, self.l1_topic_embeddings = self._load_topic_embeddings(l1_source)
        
        # 3. โหลด Maps (สำหรับ Pass 2)
        self.stdout(f"🗺️ กำลังโหลด Hierarchy Map จาก '{hierarchy_map_path}'...")
        self.hierarchy_map = self._load_json_map(hierarchy_map_path)
        
        self.stdout(f"📊 กำลังโหลด Level Map จาก '{level_map_path}'...")
        self.level_map = self._load_json_map(level_map_path)
        
        self.stdout("✅ Aggregator พร้อมใช้งาน\n")

    def _load_json_map(self, file_path: str):
        """โหลดไฟล์ JSON Map"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValueError(f"ไม่พบไฟล์ Map ที่: {file_path}")

    def _load_topic_embeddings(self, source: str):
        """โหลด L0-L1 Embeddings จาก DB"""
        self.stdout(f"📦 กำลังโหลด L0-L1 Embeddings (source='{source}')...")
        
        topics = TopicEmbedding.objects.filter(model_name=self.model_name, source=source)
        
        if not topics.exists():
            raise ValueError(f"ไม่พบ L0-L1 Embeddings (source='{source}', model='{self.model_name}')")
            
        topic_list = [t.topic_name for t in topics]
        emb_list = [np.frombuffer(t.embedding, dtype=np.float32) for t in topics]
        
        # ส่งไปที่ GPU ถ้ามี
        topic_embeddings_tensor = torch.tensor(np.vstack(emb_list), device=self.model.device)
        
        self.stdout(f"✅ โหลด L0-L1 สำเร็จ {len(topic_list):,} topics.")
        return topic_list, topic_embeddings_tensor

    def get_allowed_list(self, text: str, k=5):
        """
        (Pass 1: Top-Down)
        Classify ทั้ง abstract เทียบกับ L0-L1 topics เพื่อสร้าง "Allowed List"
        """
        if not text:
            return set()
            
        text_emb = self.model.encode(
            text, 
            convert_to_tensor=True, 
            normalize_embeddings=True
        )
        
        cos_scores = util.cos_sim(text_emb, self.l1_topic_embeddings)[0]
        
        top_results = torch.topk(cos_scores, k=k)
        
        allowed_list = set()
        for idx in top_results.indices.cpu().numpy():
            allowed_list.add(self.l1_topic_list[idx])
            
        return allowed_list

    def get_filtered_votes(self, sub_topics, allowed_list: set, max_ancestor_level=2, min_vote_count=2):
        """
        (Pass 2: Bottom-Up + Gating)
        นับคะแนนโหวตจาก Sub-topics และกรองด้วย 'Allowed List'
        """
        all_ancestors = []
        
        # 1. รวบรวมโหวตทั้งหมด
        for sub_topic in sub_topics:
            ancestors_names = self.hierarchy_map.get(sub_topic.topic_name, [])
            
            for ancestor_name in ancestors_names:
                # --- 🛡️ การกรอง Noise ด่านที่ 2 (กรอง Level) ---
                ancestor_level = self.level_map.get(ancestor_name, 99)
                if ancestor_level <= max_ancestor_level:
                    all_ancestors.append(ancestor_name)
                    
        if not all_ancestors:
            return {}

        # 2. นับคะแนน
        vote_counts = Counter(all_ancestors)
        
        # 3. กรองผลลัพธ์
        final_votes = {}
        for topic_name, votes in vote_counts.items():
            
            # --- 🛡️ การกรอง Noise ด่านที่ 3A (Gating) ---
            if topic_name not in allowed_list:
                continue
                
            # --- 🛡️ การกรอง Noise ด่านที่ 3B (Min Votes) ---
            if votes < min_vote_count:
                continue
                
            final_votes[topic_name] = votes
            
        return final_votes
    
    def find_level_0_topic(self, topic_name: str):
        """
        ค้นหา Topic Level 0 ของ topic_name ที่ระบุ
        """
        if not topic_name:
            return None
            
        # 1. ค้นหา Level ของตัวมันเอง
        level = self.level_map.get(topic_name)
        
        # 2. ถ้าตัวมันเองเป็น L0
        if level == 0:
            return topic_name
            
        # 3. ถ้าเป็น Level อื่น, ให้ค้นหาจากบรรพบุรุษ
        if level is None or level > 0:
            ancestors = self.hierarchy_map.get(topic_name, [])
            for ancestor_name in ancestors:
                # ค้นหาบรรพบุรุษตัวแรกที่เป็น Level 0
                if self.level_map.get(ancestor_name) == 0:
                    return ancestor_name # เจอแล้ว
        
        # 4. ถ้าไม่เจอ L0 (กรณีข้อมูลใน Map ไม่สมบูรณ์)
        return None