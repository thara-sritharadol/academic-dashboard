import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.cluster import AgglomerativeClustering
from sentence_transformers import SentenceTransformer
from api.models import SkillEmbedding

def build_and_save_skill_embeddings_dedup(csv_path, model_name="all-mpnet-base-v2",
                                          source="ESCO", limit=None, similarity_threshold=0.8):
    """
    โหลด skill dataset จาก .csv → encode → dedup/merge synonym → save ลงฐานข้อมูล
    """

    # --- โหลดชุดสกิลจากไฟล์
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    col_candidates = [c for c in df.columns if c.lower() in ("preferredlabel", "skill_name")]
    if not col_candidates:
        raise ValueError("ไม่พบ column ที่เป็นชื่อ skill (preferredLabel หรือ skill_name)")
    
    skills = df[col_candidates[0]].dropna().unique().tolist()
    print(f"พบ skill ทั้งหมด {len(skills):,} รายการ")

    if limit:
        skills = skills[:limit]
        print(f"จำกัดจำนวน skill ที่จะ encode: {limit}")

    # --- ทำความสะอาดเบื้องต้น
    skills = list(set([s.strip().lower() for s in skills if isinstance(s, str) and s.strip()]))

    # --- โหลดโมเดลและสร้าง embeddings
    print(f"\n🚀 กำลังโหลดโมเดล '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"📊 กำลังสร้าง embeddings สำหรับ {len(skills):,} skills ...")
    embeddings = model.encode(skills, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)

    # --- ทำ clustering เพื่อลด duplicate / synonym
    print("\n🔎 กำลังรวมกลุ่ม skill ที่มีความหมายใกล้เคียงกัน...")
    # AgglomerativeClustering ใช้ metric cosine ด้วย affinity='cosine'
    clusterer = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=1 - similarity_threshold  # cosine similarity > 0.9 → merge
    )
    labels = clusterer.fit_predict(embeddings)

    n_clusters = len(set(labels))
    print(f"✅ ได้ทั้งหมด {n_clusters:,} กลุ่ม (จาก {len(skills):,} skill เดิม)")

    # --- เลือก representative skill จากแต่ละ cluster
    merged_skills = []
    merged_embeddings = []
    for c in range(n_clusters):
        idx = np.where(labels == c)[0]
        cluster_skills = [skills[i] for i in idx]
        cluster_embs = embeddings[idx]

        # หา representative skill ที่ใกล้ center ที่สุด
        centroid = cluster_embs.mean(axis=0)
        sim = np.dot(cluster_embs, centroid)
        best_idx = idx[np.argmax(sim)]

        merged_skills.append(skills[best_idx])
        merged_embeddings.append(embeddings[best_idx])

    print(f"🧩 หลังรวม synonyms เหลือ {len(merged_skills):,} skills ที่ไม่ซ้ำกัน")

    # --- บันทึกลงฐานข้อมูล
    objs = []
    for skill, emb in tqdm(zip(merged_skills, merged_embeddings), total=len(merged_skills)):
        emb_bytes = emb.astype(np.float32).tobytes()
        objs.append(SkillEmbedding(
            skill_name=skill,
            embedding=emb_bytes,
            model_name=model_name,
            source=source
        ))

    SkillEmbedding.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
    print(f"🎉 บันทึกสำเร็จ {len(objs):,} records ลง SkillEmbedding")

    return len(objs)
