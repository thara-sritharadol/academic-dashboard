import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.cluster import AgglomerativeClustering
from api.models import SkillEmbedding

def cluster_skills_from_db(model_name="all-mpnet-base-v2", threshold=0.85, save_csv=True):
    """
    โหลด skill embeddings จาก DB แล้วทำ clustering เพื่อรวม synonyms
    Args:
        model_name: string — ชื่อโมเดลที่ใช้สร้าง embedding
        threshold: float — ค่าความคล้าย cosine ที่ต้องมากกว่าเพื่อจะถือว่าเป็นกลุ่มเดียวกัน
        save_csv: bool — ถ้า True จะบันทึกผลลัพธ์ออกเป็น CSV
    """

    print(f"🚀 เริ่มโหลด SkillEmbedding (model={model_name}) ...")
    skills = list(SkillEmbedding.objects.filter(model_name=model_name))
    if not skills:
        print("❌ ไม่พบ skill embeddings ในฐานข้อมูล")
        return

    skill_names = [s.skill_name for s in skills]
    embeddings = np.vstack([np.frombuffer(s.embedding, dtype=np.float32) for s in skills])
    print(f"📦 โหลด embeddings สำเร็จ {len(skills):,} records")

    print(f"🔎 เริ่ม clustering ด้วย threshold={threshold} ...")
    clusterer = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=1 - threshold
    )
    labels = clusterer.fit_predict(embeddings)
    n_clusters = len(set(labels))
    print(f"✅ ได้ทั้งหมด {n_clusters:,} clusters จาก {len(skills):,} skills")

    # --- สร้าง DataFrame สำหรับดู mapping
    df = pd.DataFrame({"skill_name": skill_names, "cluster_id": labels})

    # --- หา representative skill ของแต่ละ cluster
    rep_skills = []
    rep_indices = []
    for cid in tqdm(range(n_clusters), desc="เลือก representative skills"):
        idx = np.where(labels == cid)[0]
        cluster_embs = embeddings[idx]
        centroid = cluster_embs.mean(axis=0)
        sim = np.dot(cluster_embs, centroid)
        best_idx = idx[np.argmax(sim)]
        rep_skills.append(skill_names[best_idx])
        rep_indices.append(best_idx)

    df_rep = df[df["skill_name"].isin(rep_skills)].copy()
    df_rep["cluster_size"] = df.groupby("cluster_id")["skill_name"].transform("count")

    print(f"📊 ตัวแทน skill ทั้งหมด {len(df_rep):,} รายการ")

    if save_csv:
        out_path = f"skill_clusters_{model_name.replace('/', '_')}_th{threshold}.csv"
        df.to_csv(out_path, index=False)
        print(f"💾 บันทึก mapping ทั้งหมดลงไฟล์: {out_path}")

        rep_out = out_path.replace(".csv", "_representatives.csv")
        df_rep.to_csv(rep_out, index=False)
        print(f"💾 บันทึก representative skills ลงไฟล์: {rep_out}")

    return df, df_rep
