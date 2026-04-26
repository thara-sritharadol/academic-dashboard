import os
import time
import json
import requests
import boto3
from datetime import datetime

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
        """
        เปลี่ยนจากการเซฟลง DB เป็นการรวบรวมข้อมูลใส่ List แทน
        """
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

                # เก็บข้อมูลเป็น Dictionary แทนการเรียก Django Model
                author_data = {
                    "name": full_name_en,
                    "institution": "Thammasat University",
                    "faculty": staff_fac_en.strip(),
                    "email": email.strip() if email else None
                }
                all_authors.append(author_data)

            # พัก 1 วินาทีกัน API Rate Limit (เหมือนโค้ดเดิม)
            time.sleep(1)

        return all_authors

def lambda_handler(event, context):
    """
    ฟังก์ชันหลักที่ AWS Lambda จะเรียกใช้งาน
    """
    # 1. ดึงค่าตัวแปรจาก Environment Variables แทนการรับผ่าน Command Line args
    api_key = os.environ.get("TU_API_KEY")
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    
    # สามารถรับค่า specific_faculty จาก Event Trigger ได้ (ถ้ามี)
    specific_faculty = event.get("faculty")

    if not api_key or not bucket_name:
        return {"status": "error", "message": "Missing TU_API_KEY or S3_BUCKET_NAME"}

    print("Starting sync via Serverless Service...")
    
    # 2. ดึงข้อมูลผ่าน Service
    service = TUSyncService(api_key=api_key)
    authors_list = service.sync_authors_to_list(specific_faculty=specific_faculty)
    
    if not authors_list:
        return {"status": "error", "message": "No authors found or failed to fetch."}

    print(f"Fetched {len(authors_list)} authors. Uploading to S3...")

    # 3. เซฟข้อมูลเป็น JSON และอัปโหลดขึ้น S3
    s3_client = boto3.client('s3')
    
    # ตั้งชื่อไฟล์โดยใส่วันที่ เพื่อทำ Versioning ได้ง่ายๆ
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_key = f"config/tu_authors_{date_str}.json"
    
    try:
        # แปลง List เป็น JSON String แล้วดันขึ้น S3 โดยตรง (ไม่ต้องสร้างไฟล์ลงเครื่อง)
        json_data = json.dumps(authors_list, ensure_ascii=False, indent=2)

        local_folder = "local_data/config"
        os.makedirs(local_folder, exist_ok=True)
        local_file_path = f"{local_folder}/tu_authors_{date_str}.json"

        with open(local_file_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Local copy saved to: {local_file_path}")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=json_data,
            ContentType="application/json"
        )
        
        # ถ่ายสำเนาอีกไฟล์เป็นชื่อ tu_authors_latest.json เพื่อให้ Step ต่อไป (OpenAlex) เรียกใช้ไฟล์ชื่อเดิมได้เสมอ
        s3_client.put_object(
            Bucket=bucket_name,
            Key="config/tu_authors_latest.json",
            Body=json_data,
            ContentType="application/json"
        )
        
        print(f"Sync Complete! Data saved to s3://{bucket_name}/{file_key}")
        return {
            "status": "success",
            "saved_count": len(authors_list),
            "s3_path": f"s3://{bucket_name}/{file_key}"
        }
        
    except Exception as e:
        print(f"Failed to upload to S3: {e}")
        return {"status": "error", "message": str(e)}