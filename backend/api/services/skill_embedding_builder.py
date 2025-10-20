import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from api.models import SkillEmbedding

def build_and_save_skill_embeddings_from_description(
        csv_path,
        model_name="all-mpnet-base-v2",
        source="AUTO",
        limit=None
    ):

    # -------------------------------
    # 1. ตรวจสอบไฟล์
    # -------------------------------
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"📘 โหลดข้อมูลจาก {csv_path} ขนาด {len(df):,} แถว")

    required_cols = ["preferredLabel", "description"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"ไม่พบคอลัมน์ {col} ในไฟล์ ESCO CSV")

    # -------------------------------
    # 2. เตรียมข้อมูล description + mapping
    # -------------------------------
    skills = []
    skill_to_desc = {}
    desc_to_labels = {}

    for _, row in df.iterrows():
        label = str(row["preferredLabel"]).strip().lower()
        desc = str(row["description"]).strip()

        if not desc or desc.lower() in ("", "nan"):
            continue

        # บันทึก mapping จาก label → description
        skill_to_desc[label] = desc
        desc_to_labels.setdefault(desc, set()).add(label)

        # altLabels (optional)
        if "altLabels" in df.columns and pd.notna(row["altLabels"]):
            for alt in str(row["altLabels"]).splitlines():
                alt = alt.strip().lower()
                if alt:
                    skill_to_desc[alt] = desc
                    desc_to_labels[desc].add(alt)

        skills.append(desc)

    # ลบ description ซ้ำ
    unique_descs = list(set(skills))
    print(f"✅ พบ description ทั้งหมด {len(unique_descs):,} รายการ (unique)")

    if limit:
        unique_descs = unique_descs[:limit]
        print(f"📊 จำกัดจำนวน skill descriptions ที่จะ encode: {limit}")

    # -------------------------------
    # 3. โหลดโมเดลและสร้าง embeddings
    # -------------------------------
    print(f"\n🚀 กำลังโหลดโมเดล '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"📊 กำลังสร้าง embeddings สำหรับ {len(unique_descs):,} descriptions ...")
    embeddings = model.encode(
        unique_descs,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # -------------------------------
    # 4. บันทึกลงฐานข้อมูล
    # -------------------------------
    objs = []
    for desc, emb in tqdm(zip(unique_descs, embeddings), total=len(unique_descs)):
        # ใช้ preferredLabel ตัวแรกเป็นชื่อหลัก
        labels = list(desc_to_labels.get(desc, []))
        main_label = labels[0] if labels else None
        aliases = ", ".join(labels)

        emb_bytes = emb.astype(np.float32).tobytes()
        objs.append(SkillEmbedding(
            skill_name=main_label,
            embedding=emb_bytes,
            model_name=model_name,
            source=source
        ))

    SkillEmbedding.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
    print(f"🎉 บันทึกสำเร็จ {len(objs):,} records ลง SkillEmbedding")

    return len(objs)