import requests
import csv
import time
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def extract_institution_name(auth_data):
    last_known = auth_data.get("last_known_institution")
    if last_known and isinstance(last_known, dict):
        name = last_known.get("display_name")
        if name:
            return name

    affiliations = auth_data.get("affiliations")
    if affiliations and isinstance(affiliations, list):
        for aff in affiliations:
            institution = aff.get("institution")
            if institution and isinstance(institution, dict):
                name = institution.get("display_name")
                if name:
                    return name
    
    return "Unknown"

def get_institution_id(name="Thammasat University"):
    url = "https://api.openalex.org/institutions"
    params = {"search": name}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                inst = results[0]
                full_id = inst['id']
                print(f"Found Institution: {inst['display_name']} (ID: {full_id})")
                return full_id
    except Exception as e:
        print(f"Error fetching institution: {e}")
    return None

def create_retry_session():
    """สร้าง Session ที่จะลอง connect ใหม่เองอัตโนมัติถ้าเน็ตหลุด"""
    session = requests.Session()
    retries = Retry(
        total=5,              # ลองใหม่ 5 ครั้ง
        backoff_factor=1,     # รอ 1s, 2s, 4s... ก่อนลองใหม่
        status_forcelist=[500, 502, 503, 504], # ลองใหม่ถ้า Server Error
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_all_authors_cursor(institution_id):
    base_url = "https://api.openalex.org/authors"
    per_page = 100  # decrese round-trip
    
    url_filters = f"affiliations.institution.id:{institution_id}"
    
    # เริ่มต้นด้วย Cursor = * (มาตรฐาน OpenAlex)
    params = {
        "filter": url_filters,
        "per_page": per_page,
        "cursor": "*"  
    }

    session = create_retry_session()
    authors_list = []
    
    # 1. find total to create Progress Bar
    try:
        init_resp = session.get(base_url, params={**params, "per_page": 1}, timeout=10)
        total_count = init_resp.json().get("meta", {}).get("count", 0)
        print(f"Found {total_count} authors affiliated with this institution.")
    except Exception as e:
        print(f"Could not get total count: {e}")
        return []

    if total_count == 0:
        return []

    with tqdm(total=total_count, desc="Fetching Authors") as pbar:
        while True:
            try:
                resp = session.get(base_url, params=params, timeout=15)
                if resp.status_code != 200:
                    print(f"Error: Status {resp.status_code}")
                    break
                
                data = resp.json()
                results = data.get("results", [])
                
                if not results:
                    break
                
                for auth in results:
                    clean_id = auth['id'].replace("https://openalex.org/", "")

                    inst_name = extract_institution_name(auth)

                    authors_list.append({
                        "name": auth['display_name'],
                        "openalex_id": clean_id,
                        "works_count": auth['works_count'],
                        "cited_by_count": auth['cited_by_count'],
                        "last_known_institution": inst_name
                    })
                    pbar.update(1)
                
                # Update Cursor
                next_cursor = data.get("meta", {}).get("next_cursor")
                if not next_cursor:
                    break
                
                params["cursor"] = next_cursor
                
            except Exception as e:
                print(f"\nCritical Error during fetch: {e}")
                break
                
    return authors_list

if __name__ == "__main__":
    target_name = "Thammasat University"
    tu_id = get_institution_id(target_name)
    
    if tu_id:
        print("Starting robust download... (Please wait)")
        authors = fetch_all_authors_cursor(tu_id)
        
        if authors:
            filename = "tu_authors.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "openalex_id", "works_count", "cited_by_count", "last_known_institution"])
                writer.writeheader()
                writer.writerows(authors)
                
            print(f"\nSUCCESS: Saved {len(authors)} authors to {filename}")
        else:
            print("\nFAILED: No authors found.")