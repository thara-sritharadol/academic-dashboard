import os
import json
import boto3
from collections import defaultdict
from itertools import combinations
from datetime import datetime

from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.dialects.postgresql import insert

# 1. Postgres UPSERT
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

# 2. Load data from S3
def fetch_data_from_s3(bucket_name, region):
    print(f"Connecting to AWS S3 (Region: {region})...")
    s3_client = boto3.client('s3', region_name=region)

    print(f"Downloading latest authors config...")
    res_auth = s3_client.get_object(Bucket=bucket_name, Key="config/tu_authors_latest.json")
    master_authors = json.loads(res_auth['Body'].read().decode('utf-8'))

    print(f"Downloading latest processed papers...")
    res_papers = s3_client.get_object(Bucket=bucket_name, Key="results-zone/bertopic_results_latest.json")
    papers_data = json.loads(res_papers['Body'].read().decode('utf-8'))

    return master_authors, papers_data

# 3. Main ETL Process)
def main():
    print("Starting Pure Python S3-to-DB Loader...")
    
    # Config
    db_url = os.environ.get("NEONDB_URL") 
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-7")

    if not db_url or not bucket_name:
        print("Error: Missing NEONDB_URL or S3_BUCKET_NAME in environment.")
        return

    # 1. data from S3
    master_authors, papers_data = fetch_data_from_s3(bucket_name, aws_region)
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
    
    # table stata
    fac_stat_table = Table('api_facultytopicstat', metadata, autoload_with=engine)
    year_stat_table = Table('api_yearlytopicstat', metadata, autoload_with=engine)
    coauthor_table = Table('api_coauthorship', metadata, autoload_with=engine)

    # PHASE 1: Upsert Core
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

    print("Bulk Upserting Topics, Authors, Papers...")
    with engine.begin() as conn:
        upsert_bulk(conn, topics_table, list(topics_to_insert.values()), ['topic_id'], ['name', 'keywords'])
        upsert_bulk(conn, authors_table, list(authors_to_insert.values()), ['openalex_id'], ['name', 'faculty', 'institution'])
        upsert_bulk(conn, papers_table, papers_to_insert, ['doi'], ['title', 'year', 'abstract', 'citation_count'])

    # =========================================
    # PHASE 2: จัดการ Many-to-Many & คำนวณสถิติ
    # =========================================
    print("Fetching generated IDs from Database...")
    with engine.begin() as conn:
        # ดึง ID กลับมาใช้ Mapping
        paper_id_map = {row.doi: row.id for row in conn.execute(select(papers_table.c.id, papers_table.c.doi)).fetchall()}
        author_id_map = {(row.openalex_id or row.name.lower()): row.id for row in conn.execute(select(authors_table.c.id, authors_table.c.openalex_id, authors_table.c.name)).fetchall()}
        topic_id_map = {row.topic_id: row.id for row in conn.execute(select(topics_table.c.id, topics_table.c.topic_id)).fetchall()}

    # เตรียม Data สำหรับ Insert สถิติ
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
            "topic_distribution": p.get("topic_distribution", [])
        })

        # 2. แมป Author เข้า Paper และเก็บข้อมูลคณะ
        current_paper_author_ids = []
        involved_faculties = set()
        
        for a in p.get("authors_struct", []):
            key = a.get("openalex_id") or a.get("name").lower()
            a_id = author_id_map.get(key)
            if a_id:
                current_paper_author_ids.append(a_id)
                # เก็บลิงก์ M2M
                if (p_id, a_id) not in seen_links:
                    paper_author_links.append({"paper_id": p_id, "author_id": a_id})
                    seen_links.add((p_id, a_id))
                
                # หาชื่อคณะของ Author คนนี้จาก dict ที่เราเตรียมไว้
                fac = authors_to_insert[key].get("faculty")
                if fac: involved_faculties.add(fac)

        # 3. คำนวณสถิติ
        if t_db_id:
            # 3.1 Faculty Stats
            for fac in involved_faculties:
                fac_topic_counts[(fac, t_db_id)]["papers"] += 1
                fac_topic_counts[(fac, t_db_id)]["citations"] += p.get("citation_count", 0)
            
            # 3.2 Yearly Stats
            year = p.get("year")
            if year:
                yearly_counts[(year, t_db_id)] += 1

        # 4. คำนวณ Network Graph (Co-authorship)
        current_paper_author_ids.sort() # เรียงเพื่อป้องกันบั๊กคู่ (1,2) กับ (2,1)
        for id1, id2 in combinations(current_paper_author_ids, 2):
            co_authors_dict[(id1, id2)] += 1

    # =========================================
    # PHASE 3: Insert สถิติทั้งหมดลง NeonDB
    # =========================================
    print("Saving Relationships and Statistics...")
    with engine.begin() as conn:
        # Insert Paper-Author (M2M)
        if paper_author_links:
            stmt = insert(paper_authors_table).values(paper_author_links).on_conflict_do_nothing()
            conn.execute(stmt)

        # Upsert Interactions
        if interactions:
            upsert_bulk(conn, interaction_table, interactions, conflict_cols=['paper_id'], update_cols=['primary_topic_id', 'topic_distribution'])

        # Drop and Replace สถิติเพื่อความแม่นยำ 100%
        conn.execute(fac_stat_table.delete())
        conn.execute(year_stat_table.delete())
        conn.execute(coauthor_table.delete())

        if fac_topic_counts:
            current_time = datetime.now() # สร้างตัวแปรเก็บเวลาปัจจุบัน
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

    print("All Done! Dashboard data is perfectly optimized and ready.")

if __name__ == "__main__":
    main()