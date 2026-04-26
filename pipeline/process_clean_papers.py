import os
import json
import re
import boto3
from datetime import datetime
from tqdm import tqdm

def clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned_text = re.sub(r'<.*?>', ' ', text)
    cleaned_text = re.sub(r'[^\x00-\x7F]+', ' ', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = re.sub(r'\s+([.,;:?!])', r'\1', cleaned_text)
    return cleaned_text

def _reconstruct_openalex_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    max_index = 0
    for positions in inverted_index.values():
        max_index = max(max_index, max(positions))
    text_list = [""] * (max_index + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            text_list[pos] = word
    return " ".join(text_list).strip()

def flatten_authors(authorships: list) -> list:
    authors_struct = []
    if not authorships:
        return authors_struct
    for a in authorships:
        auth_node = a.get("author", {})
        name = auth_node.get("display_name", "")
        oa_id = auth_node.get("id")
        if name:
            authors_struct.append({
                "name": clean_text(name),
                "openalex_id": oa_id
            })
    return authors_struct

def main():
    # 1. from Environment Variables
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Path สำหรับ Local
    raw_file_path = f"local_data/raw-zone/{date_str}/raw_papers.json"
    local_clean_folder = f"local_data/clean-zone/{date_str}"
    local_clean_path = f"{local_clean_folder}/cleaned_papers.json"
    
    # Path สำหรับ S3
    s3_clean_key = f"clean-zone/{date_str}/cleaned_papers.json"
    s3_latest_key = "clean-zone/cleaned_papers_latest.json"

    if not os.path.exists(raw_file_path):
        print(f"Error: ไม่พบไฟล์ข้อมูลดิบที่ {raw_file_path}")
        return

    # 2. อ่านข้อมูลดิบ
    print(f"Loading raw data from {raw_file_path}...")
    with open(raw_file_path, "r", encoding="utf-8") as f:
        raw_papers = json.load(f)

    cleaned_papers = []

    # 3. Clean
    for paper in tqdm(raw_papers, desc="Cleaning Papers"):
        clean_paper_data = {
            "doi": paper.get("doi"),
            "title": clean_text(paper.get("title", "")),
            "abstract": clean_text(_reconstruct_openalex_abstract(paper.get("abstract_inverted_index"))),
            "authors_struct": flatten_authors(paper.get("authorships", [])),
            "year": paper.get("year"),
            "concepts": paper.get("concepts", [])
        }
        clean_paper_data["authors_text"] = ", ".join([a["name"] for a in clean_paper_data["authors_struct"]])
        cleaned_papers.append(clean_paper_data)

    # 4. Save to Local
    os.makedirs(local_clean_folder, exist_ok=True)
    json_data = json.dumps(cleaned_papers, ensure_ascii=False, indent=2)
    with open(local_clean_path, "w", encoding="utf-8") as f:
        f.write(json_data)
    print(f"Local copy saved to: {local_clean_path}")

    # 5. อัปโหลดขึ้น S3
    if bucket_name:
        print(f"Uploading cleaned data to S3 bucket: {bucket_name}...")
        s3_client = boto3.client('s3')
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_clean_key,
                Body=json_data,
                ContentType="application/json"
            )
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_latest_key,
                Body=json_data,
                ContentType="application/json"
            )
            print(f"S3 Upload Complete: {s3_clean_key}")
        except Exception as e:
            print(f"S3 Upload Failed: {e}")
    else:
        print("Skipped S3 upload: S3_BUCKET_NAME not set.")

if __name__ == "__main__":
    main()