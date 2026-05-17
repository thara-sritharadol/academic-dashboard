import os
import json
import time
import requests
import boto3
import argparse
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

POLITE_EMAIL = os.getenv("POLITE_EMAIL")

def get_common_headers():
    return {"User-Agent": f"TU-Research-Network-Bot/1.0 (mailto:{POLITE_EMAIL})"}

def _get_openalex_author_id(author_name: str) -> str:
    url = "https://api.openalex.org/authors"
    params = {"search": author_name}
    try:
        resp = requests.get(url, params=params, headers=get_common_headers(), timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0].get('id')
    except requests.RequestException:
        pass
    return None

def fetch_papers_for_author(author_name: str):
    base_url = "https://api.openalex.org/works"
    per_page = 50 
    papers_list = []
    
    author_id = _get_openalex_author_id(author_name)
    api_filters = [f"author.id:{author_id}"] if author_id else [f"authorships.author.search:{author_name}"]
    
    params = {
        "per_page": per_page,
        "sort": "publication_date:desc",
        "filter": ",".join(api_filters)
    }

    try:
        first_resp = requests.get(base_url, params=params, headers=get_common_headers(), timeout=10)
        if first_resp.status_code != 200:
            return []
            
        total_results = first_resp.json().get("meta", {}).get("count", 0)
        if total_results == 0:
            return []
            
        total_pages = (total_results // per_page) + 1
        
        for page in range(1, total_pages + 1):
            if (page * per_page) > 10000: break
            params["page"] = page
            
            resp = requests.get(base_url, params=params, headers=get_common_headers(), timeout=10)
            if resp.status_code != 200: break
                
            items = resp.json().get("results", [])
            for item in items:
                doi_url = item.get("doi")
                if not doi_url: continue

                # Raw Data
                papers_list.append({
                    "doi": doi_url.replace("https://doi.org/", ""),
                    "title": item.get("title", "(No Title)"),
                    "authorships": item.get("authorships", []),
                    "year": item.get("publication_year"),
                    "venue": item.get("venue_name"),
                    #"concepts": item.get("concepts", []),
                    "abstract_inverted_index": item.get("abstract_inverted_index"),
                    "citation_count": item.get("cited_by_count", 0)
                })
            time.sleep(0.5)
            
    except requests.RequestException:
        pass
        
    return papers_list

# อัปเดตให้รับ parameter source_type
def run_fetch_papers(author_limit=None, source_type=None):
    if source_type is None:
        source_type = os.getenv("DATA_SOURCE", "local").lower()

    bucket_name = os.getenv("S3_BUCKET_NAME")
    authors_data = []

    # --- เลือก Source สำหรับการอ่าน Config (tu_authors_latest.json) ---
    if source_type == "s3":
        if not bucket_name:
            print("Error: Missing S3_BUCKET_NAME environment variable.")
            return

        s3_client = boto3.client('s3')
        print(f"Downloading latest authors list from S3: s3://{bucket_name}/config/tu_authors_latest.json...")
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key="config/tu_authors_latest.json")
            authors_data = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Failed to read config from S3: {e}")
            return
    else:
        # สมมติว่าเก็บไฟล์ config ไว้ที่ local_data/config/
        local_config_path = "local_data/config/tu_authors_latest.json"
        print(f"Loading authors list from Local: {local_config_path}...")
        
        if not os.path.exists(local_config_path):
            print(f"Error: Not Found config at {local_config_path}. Please ensure the file exists.")
            return
            
        with open(local_config_path, "r", encoding="utf-8") as f:
            authors_data = json.load(f)

    if not authors_data:
        print("No authors data found.")
        return

    total_authors = len(authors_data)
    
    # --- ใช้ตัวแปร author_limit ที่รับเข้ามา ---
    if author_limit is not None and author_limit > 0:
        authors_data = authors_data[:author_limit]
        print(f"Found {total_authors} authors. (Limiting to {author_limit} authors). Starting OpenAlex fetch...")
    else:
        print(f"Found {total_authors} authors. (No limit applied). Starting OpenAlex fetch...")
    # -------------------------------------

    all_raw_papers = []
    
    for author in tqdm(authors_data, desc="Fetching Papers"):
        author_name = author.get("name")
        if not author_name: continue
        
        papers = fetch_papers_for_author(author_name)
        all_raw_papers.extend(papers)
        
        time.sleep(1.5)

    print(f"\nFetch Complete! Total papers collected: {len(all_raw_papers)}")

    # S3 Raw Zone Paths
    date_str = datetime.now().strftime("%Y-%m-%d")
    s3_raw_key = f"raw-zone/{date_str}/raw_papers.json"
    s3_latest_key = "raw-zone/raw_papers_latest.json"
    
    try:
        json_data = json.dumps(all_raw_papers, ensure_ascii=False, indent=2)

        # Save to Local
        local_folder = f"local_data/raw-zone/{date_str}"
        os.makedirs(local_folder, exist_ok=True)
        local_raw_path = f"{local_folder}/raw_papers.json"
        local_raw_latest_path = f"local_data/raw-zone/raw_papers_latest.json"

        with open(local_raw_path, "w", encoding="utf-8") as f:
            f.write(json_data)

        print(f"Local raw data saved to: {local_raw_path}")

        with open(local_raw_latest_path, "w", encoding="utf-8") as f:
            f.write(json_data)
            
        print(f"Local latest raw data saved to: {local_raw_latest_path}")

        # Put to S3
        if bucket_name:
            s3_client = boto3.client('s3')
            print(f"Uploading raw data to S3 bucket: {bucket_name}...")
            s3_client.put_object(Bucket=bucket_name, Key=s3_raw_key, Body=json_data, ContentType="application/json")
            s3_client.put_object(Bucket=bucket_name, Key=s3_latest_key, Body=json_data, ContentType="application/json")
            print(f"Raw data successfully saved to s3://{bucket_name}/{s3_raw_key}")
        else:
            print("Skipped S3 upload: S3_BUCKET_NAME not set.")

    except Exception as e:
        print(f"Failed to process and upload raw data: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch papers from OpenAlex")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of authors to fetch")
    # เพิ่ม argument --source
    parser.add_argument("--source", type=str, choices=["local", "s3"], default=None, 
                        help="Data source to fetch authors config from (local or s3)")
    args = parser.parse_args()
    
    run_fetch_papers(author_limit=args.limit, source_type=args.source)