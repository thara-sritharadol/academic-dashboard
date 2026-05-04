import os
import json
import boto3
import argparse
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

def merge_author_lists(list1: list, list2: list) -> list:
    merged_authors = {}
    
    for author in list1 + list2:
        # Use OpenAlex ID for Key, if no use low case name 
        key = author.get("openalex_id") or author.get("name", "").lower()
        
        if key not in merged_authors:
            merged_authors[key] = author
        else:
            # ถ้ามีชื่อนี้อยู่แล้ว แต่รายการใหม่มี OpenAlex ID ให้เติม ID เข้าไป
            if not merged_authors[key].get("openalex_id") and author.get("openalex_id"):
                merged_authors[key]["openalex_id"] = author.get("openalex_id")
                
    return list(merged_authors.values())

# เพิ่ม parameter source_type
def run_deduplicate(source_type=None):
    if source_type is None:
        source_type = os.getenv("DATA_SOURCE", "local").lower()

    bucket_name = os.getenv("S3_BUCKET_NAME")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    cleaned_papers = []

    # --- เลือก Source สำหรับการอ่านไฟล์ (cleaned_papers_latest.json) ---
    if source_type == "s3":
        if not bucket_name:
            print("Error: Missing S3_BUCKET_NAME environment variable.")
            return

        s3_client = boto3.client('s3')
        s3_clean_key = "clean-zone/cleaned_papers_latest.json"
        
        print(f"Loading cleaned data from S3: s3://{bucket_name}/{s3_clean_key}...")
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=s3_clean_key)
            cleaned_papers = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Failed to read cleaned data from S3: {e}")
            return
    
    else:
        # ปรับให้อ่านไฟล์จาก latest ทันที
        clean_file_path = "local_data/clean-zone/cleaned_papers_latest.json"
        print(f"Loading cleaned data from Local: {clean_file_path}...")
        
        if not os.path.exists(clean_file_path):
            print(f"Error: ไม่พบไฟล์ที่คลีนแล้วที่ {clean_file_path}")
            return
            
        with open(clean_file_path, "r", encoding="utf-8") as f:
            cleaned_papers = json.load(f)

    if not cleaned_papers:
        print("No data found to deduplicate.")
        return

    print("Starting deduplication process...")
    
    unique_papers_by_doi = {}
    unique_papers_by_title = {}
    
    total_merged = 0

    for paper in tqdm(cleaned_papers, desc="Deduplicating"):
        doi = paper.get("doi")
        title_lower = paper.get("title", "").lower()
        
        is_duplicate = False
        target_paper = None
        
        # 1. เช็กซ้ำด้วย DOI
        if doi and doi in unique_papers_by_doi:
            target_paper = unique_papers_by_doi[doi]
            is_duplicate = True
            
        # 2. เช็กซ้ำด้วย Title (กรณีไม่มี DOI)
        elif title_lower and title_lower in unique_papers_by_title:
            target_paper = unique_papers_by_title[title_lower]
            is_duplicate = True

        if is_duplicate:
            # === ลอจิกการ Merge Paper ===
            # รวมรายชื่อ Authors จาก Paper ใหม่เข้ากับ Paper เดิม
            target_paper["authors_struct"] = merge_author_lists(
                target_paper.get("authors_struct", []), 
                paper.get("authors_struct", [])
            )
            # อัปเดต authors_text ให้เป็นปัจจุบัน
            target_paper["authors_text"] = ", ".join([a["name"] for a in target_paper["authors_struct"]])
            
            # (ถ้า Paper ใหม่มี Abstract แต่ Paper เดิมไม่มี ให้เอามาถม)
            if not target_paper.get("abstract") and paper.get("abstract"):
                target_paper["abstract"] = paper.get("abstract")
                
            total_merged += 1
        else:
            # === ไม่ซ้ำ: เก็บเป็นรายการใหม่ ===
            if doi:
                unique_papers_by_doi[doi] = paper
            elif title_lower:
                unique_papers_by_title[title_lower] = paper

    # รวม Paper ทั้งหมดที่รอดจากการคัดกรองกลับมาเป็น List
    final_papers = list(unique_papers_by_doi.values()) + list(unique_papers_by_title.values())
    
    print(f"\nDeduplication Complete!")
    print(f"   - Original Papers: {len(cleaned_papers)}")
    print(f"   - Duplicates Merged: {total_merged}")
    print(f"   - Final Unique Papers: {len(final_papers)}")

    # Paths สำหรับ Local & S3 Output
    dedupe_folder = f"local_data/dedupe-zone/{date_str}"
    dedupe_file_path = f"{dedupe_folder}/deduplicated_papers.json"
    local_dedupe_latest_path = "local_data/dedupe-zone/deduplicated_papers_latest.json"
    
    s3_dedupe_key = f"dedupe-zone/{date_str}/deduplicated_papers.json"
    s3_latest_key = "dedupe-zone/deduplicated_papers_latest.json"

    # เซฟลงเครื่อง Local
    os.makedirs(dedupe_folder, exist_ok=True)
    json_data = json.dumps(final_papers, ensure_ascii=False, indent=2)

    with open(dedupe_file_path, "w", encoding="utf-8") as f:
        f.write(json_data)
    print(f"Local copy saved to: {dedupe_file_path}")

    with open(local_dedupe_latest_path, "w", encoding="utf-8") as f:
        f.write(json_data)
    print(f"Local latest copy saved to: {local_dedupe_latest_path}")

    # อัปโหลดขึ้น S3
    if bucket_name:
        # สร้าง client เผื่อกรณีที่ตอนแรกอ่านจาก Local 
        s3_client = boto3.client('s3') 
        print(f"Uploading deduplicated data to S3 bucket: {bucket_name}...")
        try:
            s3_client.put_object(Bucket=bucket_name, Key=s3_dedupe_key, Body=json_data, ContentType="application/json")
            s3_client.put_object(Bucket=bucket_name, Key=s3_latest_key, Body=json_data, ContentType="application/json")
            print(f"S3 Upload Complete: {s3_dedupe_key}")
        except Exception as e:
            print(f"S3 Upload Failed: {e}")
    else:
         print("Skipped S3 upload: S3_BUCKET_NAME not set.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate cleaned papers data")
    parser.add_argument("--source", type=str, choices=["local", "s3"], default=None, 
                        help="Data source to fetch cleaned files from (local or s3)")
    args = parser.parse_args()
    
    run_deduplicate(source_type=args.source)