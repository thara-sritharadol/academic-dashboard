import os
import json
import boto3
import argparse
from collections import defaultdict
from itertools import combinations
from datetime import datetime
from dotenv import load_dotenv

# เพิ่ม text เข้ามาเพื่อใช้รันคำสั่ง SQL ดิบ (Raw SQL)
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.dialects.postgresql import insert

load_dotenv()

# 1. Postgres UPSERT (ยังคงไว้ใช้จัดการกรณีข้อมูลซ้ำกันเองภายในไฟล์ JSON ใหม่)
def upsert_bulk(conn, table, data_list, conflict_cols, update_cols):
    """Bulk Upsert (Insert or Update)"""
    if not data_list: return
    stmt = insert(table).values(data_list)
    update_dict = {col: getattr(stmt.excluded, col) for col in update_cols}
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_=update_dict
    )
    conn.execute(upsert_stmt)

# 2. Load data
def fetch_data(source_type, bucket_name, region=None):
    master_authors = []
    papers_data = []

    if source_type == "s3":
        if not bucket_name:
             print("Error: Missing S3_BUCKET_NAME in environment for S3 data fetch.")
             return [], []
             
        print(f"Connecting to AWS S3 (Region: {region})...")
        s3_client = boto3.client('s3', region_name=region)

        print(f"Downloading latest authors config from S3...")
        try:
            res_auth = s3_client.get_object(Bucket=bucket_name, Key="config/tu_authors_latest.json")
            master_authors = json.loads(res_auth['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Failed to fetch authors config from S3: {e}")

        print(f"Downloading latest processed papers from S3...")
        try:
            res_papers = s3_client.get_object(Bucket=bucket_name, Key="results-zone/bertopic_results_latest.json")
            papers_data = json.loads(res_papers['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Failed to fetch processed papers from S3: {e}")

    else:
        # Load from Local
        print("Loading data from Local...")
        
        local_auth_path = "local_data/config/tu_authors_latest.json"
        local_papers_path = "local_data/results-zone/bertopic_results_latest.json" 

        # Fallback case
        date_str = datetime.now().strftime("%Y-%m-%d")
        fallback_papers_path = f"local_data/results-zone/{date_str}/bertopic_results.json"


        try:
            with open(local_auth_path, "r", encoding="utf-8") as f:
                master_authors = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Authors config not found at {local_auth_path}")
            
        target_papers_path = local_papers_path if os.path.exists(local_papers_path) else fallback_papers_path
        
        try:
            with open(target_papers_path, "r", encoding="utf-8") as f:
                papers_data = json.load(f)
        except FileNotFoundError:
             print(f"Warning: Processed papers not found at {target_papers_path}")

    return master_authors, papers_data

# 3. Main ETL Process
def load_to_db(source_type=None):
    if source_type is None:
        source_type = os.getenv("DATA_SOURCE", "local").lower()
        
    print(f"Starting Pure Python Loader... (Source: {source_type.upper()})")
    
    # Config
    db_url = os.getenv("DATABASE_URL") 
    bucket_name = os.getenv("S3_BUCKET_NAME")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-7")

    if not db_url:
        print("Error: Missing DATABASE_URL in environment.")
        return

    # 1. data
    master_authors, papers_data = fetch_data(source_type, bucket_name, aws_region)
    
    if not papers_data:
        print("Error: No paper data found to process.")
        return
        
    faculty_map = { a["name"].lower(): a.get("faculty") for a in master_authors }

    # 2. db
    engine = create_engine(db_url)
    metadata = MetaData()
    
    print("Reflecting Schema from DB...")
    topics_table = Table('api_topic', metadata, autoload_with=engine)
    authors_table = Table('api_author', metadata, autoload_with=engine)
    papers_table = Table('api_paper', metadata, autoload_with=engine)
    paper_authors_table = Table('api_paper_authors', metadata, autoload_with=engine)
    interaction_table = Table('api_papertopicinteraction', metadata, autoload_with=engine)
    
    fac_stat_table = Table('api_facultytopicstat', metadata, autoload_with=engine)
    year_stat_table = Table('api_yearlytopicstat', metadata, autoload_with=engine)
    coauthor_table = Table('api_coauthorship', metadata, autoload_with=engine)

    # =========================================
    # PHASE 0: WIPE OLD DATA (FULL REFRESH)
    # =========================================
    print("Wiping existing data from Database (TRUNCATE & RESTART IDENTITY)...")
    with engine.begin() as conn:
        # ใช้ TRUNCATE CASCADE เพื่อลบข้อมูลทุกตารางที่เกี่ยวข้องกัน และเริ่ม ID ใหม่
        conn.execute(text("""
            TRUNCATE TABLE 
                api_facultytopicstat, 
                api_yearlytopicstat, 
                api_coauthorship,
                api_papertopicinteraction, 
                api_paper_authors, 
                api_paper, 
                api_author, 
                api_topic 
            RESTART IDENTITY CASCADE;
        """))
    print("Old data has been completely removed.")

    # =========================================
    # PHASE 1: Prepare & Insert Core Data
    # =========================================
    topics_to_insert, authors_to_insert, papers_to_insert = {}, {}, []
    
    print("Preparing Core Data...")
    for p in papers_data:
        # prepare Topic
        t_id = p.get("cluster_id", -1)
        t_label = p.get("cluster_label", "Outlier / Noise")
        clean_name = t_label.split(": ", 1)[-1] if ": " in t_label else t_label
        topics_to_insert[t_id] = {"topic_id": t_id, "name": clean_name, "keywords": p.get("topic_keywords", [])}

        # prepare Paper
        doi = p.get("doi")
        papers_to_insert.append({
            "doi": doi, "title": p.get("title", ""), "year": p.get("year"),
            "abstract": p.get("abstract", ""), "citation_count": p.get("citation_count", 0),
            "url": p.get("url", ""), "citation_count": p.get("citation_count", 0)
        })

        # เตรียม Author
        for a in p.get("authors_struct", []):
            a_name = a.get("name")
            a_id = a.get("openalex_id")
            key = a_id or a_name.lower()
            if key not in authors_to_insert:
                fac = faculty_map.get(a_name.lower())
                authors_to_insert[key] = {
                    "openalex_id": a_id, "name": a_name, "faculty": fac,
                    "institution": "Thammasat University" if fac else "External", "email": None
                }

    print("Inserting Core Data (Topics, Authors, Papers)...")
    with engine.begin() as conn:
        # ยังคงใช้ upsert_bulk เพื่อป้องกัน Error กรณีข้อมูลในไฟล์ JSON มีการดึงข้อมูลซ้ำกันเอง (Intra-file duplicates)
        upsert_bulk(conn, topics_table, list(topics_to_insert.values()), ['topic_id'], ['name', 'keywords'])
        upsert_bulk(conn, authors_table, list(authors_to_insert.values()), ['openalex_id'], ['name', 'faculty', 'institution'])
        upsert_bulk(conn, papers_table, papers_to_insert, ['doi'], ['title', 'year', 'abstract', 'citation_count'])

    # =========================================
    # PHASE 2: จัดการ Many-to-Many & คำนวณสถิติ
    # =========================================
    print("Fetching generated IDs from Database...")
    with engine.begin() as conn:
        paper_id_map = {row.doi: row.id for row in conn.execute(select(papers_table.c.id, papers_table.c.doi)).fetchall()}
        author_id_map = {(row.openalex_id or row.name.lower()): row.id for row in conn.execute(select(authors_table.c.id, authors_table.c.openalex_id, authors_table.c.name)).fetchall()}
        topic_id_map = {row.topic_id: row.id for row in conn.execute(select(topics_table.c.id, topics_table.c.topic_id)).fetchall()}

    paper_author_links = []
    interactions = []
    seen_links = set()
    
    fac_topic_counts = defaultdict(lambda: {"papers": 0, "citations": 0})
    yearly_counts = defaultdict(int)
    co_authors_dict = defaultdict(int)

    print("Processing Relationships and Aggregations...")
    for p in papers_data:
        p_id = paper_id_map.get(p.get("doi"))
        if not p_id: continue

        t_db_id = topic_id_map.get(p.get("cluster_id", -1))
        
        # 1. สร้าง interaction (BERTopic ผลลัพธ์)
        interactions.append({
            "paper_id": p_id,
            "primary_topic_id": t_db_id,
            "topic_distribution": p.get("topic_distribution", []),
            "predicted_multi_labels": p.get("predicted_multi_labels", [])
        })

        # 2. แมป Author เข้า Paper
        current_paper_author_ids = []
        involved_faculties = set()
        
        for a in p.get("authors_struct", []):
            key = a.get("openalex_id") or a.get("name").lower()
            a_id = author_id_map.get(key)
            if a_id:
                current_paper_author_ids.append(a_id)
                if (p_id, a_id) not in seen_links:
                    paper_author_links.append({"paper_id": p_id, "author_id": a_id})
                    seen_links.add((p_id, a_id))
                
                fac = authors_to_insert[key].get("faculty")
                if fac: involved_faculties.add(fac)

        # 3. คำนวณสถิติ
        if t_db_id:
            for fac in involved_faculties:
                fac_topic_counts[(fac, t_db_id)]["papers"] += 1
                fac_topic_counts[(fac, t_db_id)]["citations"] += p.get("citation_count", 0)
            
            year = p.get("year")
            if year:
                yearly_counts[(year, t_db_id)] += 1

        # 4. คำนวณ Network Graph (Co-authorship)
        current_paper_author_ids.sort() 
        for id1, id2 in combinations(current_paper_author_ids, 2):
            co_authors_dict[(id1, id2)] += 1

    # =========================================
    # PHASE 3: Insert สถิติทั้งหมด
    # =========================================
    print("Saving Relationships and Statistics...")
    with engine.begin() as conn:
        if paper_author_links:
            stmt = insert(paper_authors_table).values(paper_author_links).on_conflict_do_nothing()
            conn.execute(stmt)

        if interactions:
            upsert_bulk(
                conn,
                interaction_table,
                interactions,
                conflict_cols=['paper_id'],
                update_cols=['primary_topic_id', 'topic_distribution', 'predicted_multi_labels']
            )

        # ตัดการ .delete() สถิติออกไป เพราะเราเคลียร์หมดแล้วใน Phase 0
        if fac_topic_counts:
            current_time = datetime.now()
            fac_data = [
                {
                    "faculty": f, 
                    "topic_id": t, 
                    "total_papers": v["papers"], 
                    "total_citations": v["citations"],
                    "last_updated": current_time
                } 
                for (f, t), v in fac_topic_counts.items()
            ]
            conn.execute(insert(fac_stat_table).values(fac_data))

        if yearly_counts:
            year_data = [{"year": y, "topic_id": t, "total_papers": c} for (y, t), c in yearly_counts.items()]
            conn.execute(insert(year_stat_table).values(year_data))

        if co_authors_dict:
            coauth_data = [{"author_a_id": a1, "author_b_id": a2, "weight": w} for (a1, a2), w in co_authors_dict.items()]
            conn.execute(insert(coauthor_table).values(coauth_data))

    print("All Done! Dashboard data has been fully refreshed and is ready.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load processed data to Database")
    parser.add_argument("--source", type=str, choices=["local", "s3"], default=None, 
                        help="Data source to fetch from (local or s3)")
    args = parser.parse_args()
    
    load_to_db(source_type=args.source)