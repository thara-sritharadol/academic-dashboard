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
    โหลด skill dataset จาก .csv → รวม preferredLabel + altLabels + description → encode → dedup/merge synonym → save ลงฐานข้อมูล
    """

    # --- ตรวจสอบไฟล์
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"📘 โหลดข้อมูลจาก {csv_path} ขนาด {len(df):,} แถว")

    if "preferredLabel" not in df.columns:
        raise ValueError("ไม่พบคอลัมน์ preferredLabel ในไฟล์ ESCO CSV")

    # --- สร้างรายการ skills โดยรวม altLabels + description (ถ้ามี)
    print("🧩 กำลังรวม preferredLabel + altLabels + description ...")
    skills = []
    canonical_map = {}

    for _, row in df.iterrows():
        if pd.isna(row["preferredLabel"]):
            continue

        base_skill = row["preferredLabel"].strip().lower()
        desc = ""
        if "description" in df.columns and pd.notna(row["description"]):
            desc = str(row["description"]).strip()

        # รวมชื่อและคำอธิบายเข้าด้วยกัน
        base_text = f"{base_skill}. {desc}" if desc else base_skill
        skills.append(base_text)

        # รวม altLabels ทั้งหมดเป็น synonym ของ base skill
        if "altLabels" in df.columns and pd.notna(row["altLabels"]):
            for alt in str(row["altLabels"]).split("|"):
                alt = alt.strip().lower()
                if not alt:
                    continue
                alt_text = f"{alt}. {desc}" if desc else alt
                canonical_map[alt_text] = base_skill
                skills.append(alt_text)

    # --- ทำความสะอาดและจำกัดจำนวน
    skills = list(set([s for s in skills if isinstance(s, str) and s.strip()]))
    print(f"✅ รวม skill ทั้งหมด {len(skills):,} รายการ (รวม synonyms และ descriptions)")

    if limit:
        skills = skills[:limit]
        print(f"📊 จำกัดจำนวน skill ที่จะ encode: {limit}")

    # --- โหลดโมเดลและสร้าง embeddings
    print(f"\n🚀 กำลังโหลดโมเดล '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"📊 กำลังสร้าง embeddings สำหรับ {len(skills):,} skills ...")
    embeddings = model.encode(
        skills, 
        convert_to_numpy=True, 
        show_progress_bar=True, 
        normalize_embeddings=True
    )

    # --- ทำ clustering เพื่อลด duplicate / synonym
    print("\n🔎 กำลังรวมกลุ่ม skill ที่มีความหมายใกล้เคียงกัน...")
    clusterer = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=1 - similarity_threshold
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

        centroid = cluster_embs.mean(axis=0)
        sim = np.dot(cluster_embs, centroid)
        best_idx = idx[np.argmax(sim)]
        rep_skill = skills[best_idx]

        # ถ้ามี canonical map ให้ใช้ชื่อหลักแทน
        if rep_skill in canonical_map:
            rep_skill = canonical_map[rep_skill]

        # ลบ description ออกจากชื่อก่อนบันทึก (เหลือแต่ชื่อสกิลหลัก)
        rep_skill = rep_skill.split(".")[0].strip()

        merged_skills.append(rep_skill)
        merged_embeddings.append(embeddings[best_idx])

    print(f"🧠 หลังรวม synonyms เหลือ {len(merged_skills):,} skills ที่ไม่ซ้ำกัน")

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
