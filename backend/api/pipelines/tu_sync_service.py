import time
import requests
from api.models import Author

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

    def sync_authors(self, specific_faculty=None):
        faculties_to_process = []
        if specific_faculty:
            faculties_to_process.append({"faculty_en": specific_faculty})
        else:
            faculties_to_process = self.fetch_faculties()

        if not faculties_to_process:
            return {"status": "error", "message": "No faculties found to process."}

        total_saved, total_updated = 0, 0

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

                author_obj, created = Author.objects.update_or_create(
                    name=full_name_en,
                    defaults={
                        "institution": "Thammasat University",
                        "faculty": staff_fac_en.strip(),
                        "email": email.strip() if email else None
                    }
                )
                
                if created:
                    total_saved += 1
                else:
                    total_updated += 1

            time.sleep(1)

        return {
            "status": "success",
            "saved": total_saved,
            "updated": total_updated
        }