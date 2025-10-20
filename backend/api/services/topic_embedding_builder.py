import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
# ## NEW ##: สมมติว่าสร้างโมเดลใหม่ชื่อ TopicEmbedding
from api.models import TopicEmbedding 

def build_and_save_topic_embeddings(
        csv_path, # ไฟล์ topics.csv
        model_name="all-mpnet-base-v2",
        source="MANUAL_TOPICS", # ระบุแหล่งที่มาของ topic
        limit=None
    ):

    # -------------------------------
    # 1. ตรวจสอบไฟล์
    # -------------------------------
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"📘 โหลดข้อมูล Topics จาก {csv_path} ขนาด {len(df):,} แถว")

    # ## CHANGED ##: เปลี่ยนคอลัมน์ที่ต้องการ
    required_cols = ["topic_name", "topic_description"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"ไม่พบคอลัมน์ {col} ในไฟล์ CSV")

    # -------------------------------
    # 2. เตรียมข้อมูล (ใช้ description ของ topic)
    # -------------------------------
    # ## CHANGED ##: Logic ง่ายขึ้นมาก
    topics = df['topic_name'].tolist()
    descriptions = df['topic_description'].tolist()

    if limit:
        topics = topics[:limit]
        descriptions = descriptions[:limit]
        print(f"📊 จำกัดจำนวน topics ที่จะ encode: {limit}")

    # -------------------------------
    # 3. โหลดโมเดลและสร้าง embeddings
    # -------------------------------
    print(f"\n🚀 กำลังโหลดโมเดล '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"📊 กำลังสร้าง embeddings สำหรับ {len(descriptions):,} topic descriptions ...")
    embeddings = model.encode(
        descriptions, # ใช้ description ในการสร้าง embedding เพื่อความหมายที่สมบูรณ์
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # -------------------------------
    # 4. บันทึกลงฐานข้อมูล
    # -------------------------------
    objs = []
    # ## CHANGED ##: วนลูปตาม topic และ embedding
    for topic_name, emb in tqdm(zip(topics, embeddings), total=len(topics)):
        emb_bytes = emb.astype(np.float32).tobytes()
        objs.append(TopicEmbedding( # บันทึกลง Model ใหม่
            topic_name=topic_name,
            embedding=emb_bytes,
            model_name=model_name,
            source=source
        ))

    TopicEmbedding.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
    print(f"🎉 บันทึกสำเร็จ {len(objs):,} records ลง TopicEmbedding")

    return len(objs)