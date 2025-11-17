import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from api.models import SkillEmbedding 

def build_and_save_skill_embeddings(
        csv_path,
        model_name="all-mpnet-base-v2",
        source="MANUAL_SKILLS",
        limit=None
    ):

    #Check file
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"Load topics from {csv_path} size {len(df):,} row")

    required_cols = ["topic_name", "topic_description"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"No Found {col} Column in CSV file")

    #Clean Data
    df = df.dropna(subset=["topic_name", "topic_description"])
    df = df.reset_index(drop=True) #Reset index
    
    original_count = len(df)

    if limit:
        df = df.head(limit)
        print(f"litmit skills to encode: {limit} (from {original_count:,})")
    else:
        print(f"Found {original_count:,} valid topics to process.")

    #Prepare data (using weighted logic)
    print("Prepare the text to encode (topic_name + topic_name + topic_description)")
    
    #create real text to encode
    df["text_to_encode"] = df["topic_name"] + ". " + df["topic_name"] + ". " + df["topic_description"]
    
    #list to encode
    texts_to_encode = df["text_to_encode"].tolist()
    
    topics_for_db = df['topic_name'].tolist()

    #Load Model and Create Embedding
    print(f"\nLoading '{model_name}' ...")
    model = SentenceTransformer(model_name)

    print(f"Creating embeddings for {len(texts_to_encode):,} topics ...")
    embeddings = model.encode(
        texts_to_encode,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    #Save to DB
    objs = []
    for skill_name, emb in tqdm(zip(topics_for_db, embeddings), total=len(topics_for_db)):
        emb_bytes = emb.astype(np.float32).tobytes()
        objs.append(SkillEmbedding(
            skill_name=skill_name,
            embedding=emb_bytes,
            model_name=model_name,
            source=source
        ))

    SkillEmbedding.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
    print(f"Save {len(objs):,} records to SkillEmbedding Successfully")

    return len(objs)