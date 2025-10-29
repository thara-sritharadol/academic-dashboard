import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from api.models import TopicEmbedding 

def build_and_save_topic_embeddings(
        csv_path,
        model_name="allenai/specter2_base", # <-- ค่า default ตรงกับ Colab
        source="MANUAL_TOPICS",
        limit=None
    ):

    # -------------------------------
    # 1. ตรวจสอบไฟล์ (เหมือนเดิม)
    # -------------------------------
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"📘 โหลดข้อมูล Topics จาก {csv_path} ขนาด {len(df):,} แถว")

    required_cols = ["topic_name", "topic_description"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"ไม่พบคอลัมน์ {col} ในไฟล์ CSV")

    # ## NEW ##: ทำความสะอาดข้อมูลเหมือนใน Colab
    df = df.dropna(subset=["topic_name", "topic_description"])
    df = df.reset_index(drop=True) # Reset index หลัง dropna
    
    original_count = len(df)

    if limit:
        df = df.head(limit)
        print(f"📊 จำกัดจำนวน topics ที่จะ encode: {limit} (จาก {original_count:,})")
    else:
        print(f"Found {original_count:,} valid topics to process.")


    # -------------------------------
    # 2. ## CHANGED ##: เตรียมข้อมูล (ใช้ตรรกะถ่วงน้ำหนักแบบ Colab)
    # -------------------------------
    print("💡 เตรียมข้อความสำหรับ encode (topic_name + topic_name + topic_description)")
    
    # สร้าง text ที่จะใช้ encode จริง
    df["text_to_encode"] = df["topic_name"] + ". " + df["topic_name"] + ". " + df["topic_description"]
    
    # ดึง list ข้อความไป encode
    texts_to_encode = df["text_to_encode"].tolist()
    
    # ดึง list ชื่อ topic ไปใช้ตอนบันทึก
    topics_for_db = df['topic_name'].tolist()

    # -------------------------------
    # 3. ## CHANGED ##: โหลดโมเดลและสร้าง embeddings
    # -------------------------------
    print(f"\n🚀 กำลังโหลดโมเดล '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"📊 กำลังสร้าง embeddings สำหรับ {len(texts_to_encode):,} topics ...")
    embeddings = model.encode(
        texts_to_encode, # <-- ใช้ text ที่ผ่านการถ่วงน้ำหนักแล้ว
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # -------------------------------
    # 4. ## CHANGED ##: บันทึกลงฐานข้อมูล (ใช้ topics_for_db)
    # -------------------------------
    objs = []
    # วนลูปโดยใช้ชื่อ topic จาก list ที่เตรียมไว้
    for topic_name, emb in tqdm(zip(topics_for_db, embeddings), total=len(topics_for_db)):
        emb_bytes = emb.astype(np.float32).tobytes()
        objs.append(TopicEmbedding(
            topic_name=topic_name,
            embedding=emb_bytes,
            model_name=model_name,
            source=source
        ))

    TopicEmbedding.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
    print(f"🎉 บันทึกสำเร็จ {len(objs):,} records ลง TopicEmbedding")

    return len(objs)