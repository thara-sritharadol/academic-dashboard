import os
import time
import json
import requests
import boto3
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class TUSyncService:
    def __init__(self, api_key):
        self.headers = {
            "Content-Type": "application/json",
            "Application-Key": api_key
        }

    def fetch_faculties(self):
        url = "https://restapi.tu.ac.th/api/v2/std/fac/all" 
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            res.raise_for_status()
            data = res.json()
            return data.get('data', []) if data.get('status') else []
        except Exception as e:
            print(f"Error fetching faculties: {e}")
            return []

    def fetch_instructors(self, faculty_en):
        url = "https://restapi.tu.ac.th/api/v2/profile/Instructors/info/"
        params = {"Faculty_Name_En": faculty_en} 
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=15)
            if res.status_code != 200:
                return []
            data = res.json()
            return data.get('data', []) if data.get('status') else []
        except Exception as e:
            print(f"Could not fetch instructors for {faculty_en}: {e}")
            return []

    def sync_authors_to_list(self, specific_faculty=None):
        faculties_to_process = []
        if specific_faculty:
            faculties_to_process.append({"faculty_en": specific_faculty})
        else:
            faculties_to_process = self.fetch_faculties()

        if not faculties_to_process:
            return []

        all_authors = []

        for fac in faculties_to_process:
            fac_en = fac.get("faculty_en")
            if not fac_en:
                continue

            instructors = self.fetch_instructors(fac_en)

            for staff in instructors:
                first_en = staff.get("First_Name_En")
                last_en = staff.get("Last_Name_En")
                email = staff.get("Email")
                
                if not first_en or not last_en:
                    continue

                full_name_en = f"{first_en.strip()} {last_en.strip()}"
                staff_fac_en = staff.get("Faculty_Name_En") or fac_en

                author_data = {
                    "name": full_name_en,
                    "institution": "Thammasat University",
                    "faculty": staff_fac_en.strip(),
                    "email": email.strip() if email else None
                }
                all_authors.append(author_data)

            # API Rate Limit
            time.sleep(1)

        return all_authors

def run_find_researcher(faculty):
    # Environment Variables
    api_key = os.getenv("TU_API_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME")
    
    # specific_faculty
    specific_faculty = faculty

    if not api_key:
        return {"status": "error", "message": "Missing TU_API_KEY"}

    print("Starting sync via Serverless Service...")
    
    service = TUSyncService(api_key=api_key)
    authors_list = service.sync_authors_to_list(specific_faculty=specific_faculty)
    
    if not authors_list:
        return {"status": "error", "message": "No authors found or failed to fetch."}

    print(f"Fetched {len(authors_list)} authors.")

    # for Versioning
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_key = f"config/tu_authors_{date_str}.json"
    
    try:
        # List to JSON String
        json_data = json.dumps(authors_list, ensure_ascii=False, indent=2)

        local_folder = "local_data/config"
        os.makedirs(local_folder, exist_ok=True)
        
        # 1. บันทึกไฟล์แบบมีวันที่บน Local
        local_file_path = f"{local_folder}/tu_authors_{date_str}.json"
        with open(local_file_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Local versioned copy saved to: {local_file_path}")

        # 2. บันทึกไฟล์ latest บน Local (เพิ่มใหม่)
        local_latest_path = f"{local_folder}/tu_authors_latest.json"
        with open(local_latest_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Local latest copy saved to: {local_latest_path}")

        # Put to S3 (ทำเฉพาะเมื่อมีการตั้งค่า S3_BUCKET_NAME ไว้)
        if bucket_name:
            print("Uploading to S3...")
            s3_client = boto3.client('s3')
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=json_data,
                ContentType="application/json"
            )
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key="config/tu_authors_latest.json",
                Body=json_data,
                ContentType="application/json"
            )
            print(f"Sync Complete! Data saved to s3://{bucket_name}/{file_key}")
            s3_path = f"s3://{bucket_name}/{file_key}"
        else:
            print("Skipped S3 upload: S3_BUCKET_NAME not set.")
            s3_path = None

        return {
            "status": "success",
            "saved_count": len(authors_list),
            "s3_path": s3_path,
            "local_latest_path": local_latest_path
        }
        
    except Exception as e:
        print(f"Failed to process and save data: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test run
    parser = argparse.ArgumentParser(description="Find Prof. from Thammasat University")
    parser.add_argument("--faculty", type=str, default="Faculty of Science and Technology", help="Faculty to fetch Prof.")
    args = parser.parse_args()
    run_find_researcher(args.faculty)