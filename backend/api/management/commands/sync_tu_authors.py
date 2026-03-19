import time
import requests
from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Author

class Command(BaseCommand):
    help = "Fetch all faculties and authors from TU API and save to the local database"

    def add_arguments(self, parser):
        # Access Token
        parser.add_argument("--api_key", type=str, required=True, help="TU API Access Token")
        parser.add_argument("--faculty", type=str, help="Specific Faculty_Name_En to fetch (e.g., 'Faculty of Law')")

    def fetch_faculties(self, headers):
        TU_FACULTY_API_URL = "https://restapi.tu.ac.th/api/v2/std/fac/all" 
        
        self.stdout.write(self.style.NOTICE("Fetching faculty list..."))
        try:
            res = requests.get(TU_FACULTY_API_URL, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()
            if data.get('status'):
                return data.get('data', [])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching faculties: {e}"))
        return []

    def fetch_instructors(self, faculty_en, headers):
        TU_INSTRUCTORS_API_URL = "https://restapi.tu.ac.th/api/v2/profile/Instructors/info/"
        
        params = {"Faculty_Name_En": faculty_en} 
        
        try:
            res = requests.get(TU_INSTRUCTORS_API_URL, headers=headers, params=params, timeout=15)
            # If a faculty doesn't have API information, they might return a 404 error, so we'll skip that.
            if res.status_code != 200:
                return []
                
            data = res.json()
            if data.get('status'):
                return data.get('data', [])
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"\nCould not fetch instructors for {faculty_en}: {e}"))
        return []

    def handle(self, *args, **options):
        api_key = options.get("api_key")
        specific_faculty = options.get("faculty")

        # Set headers according to the TU API.
        headers = {
            "Content-Type": "application/json",
            "Application-Key": api_key
        }

        faculties_to_process = []

        # Prepare the list of faculties.
        if specific_faculty:
            # If type --faculty, it will only retrieve one entry.
            faculties_to_process.append({"faculty_en": specific_faculty})
        else:
            # If not specified, retrieve all faculty names from the API first.
            faculties_to_process = self.fetch_faculties(headers)
            if not faculties_to_process:
                self.stdout.write(self.style.ERROR("No faculties found to process. Exiting."))
                return

        self.stdout.write(self.style.NOTICE(f"Starting sync for {len(faculties_to_process)} faculties..."))

        total_saved = 0
        total_updated = 0

        # Loop through each faculty to retrieve the list of professors.
        for fac in tqdm(faculties_to_process, desc="Processing Faculties", unit="faculty"):
            fac_en = fac.get("faculty_en")
            if not fac_en:
                continue

            # Requesting information about professors in this faculty via API.
            instructors = self.fetch_instructors(fac_en, headers)

            # Record the professors. information into database.
            for staff in instructors:
                first_en = staff.get("First_Name_En")
                last_en = staff.get("Last_Name_En")
                email = staff.get("Email")
                
                # Prevent cases where the API returns a null value.
                if not first_en or not last_en:
                    continue

                full_name_en = f"{first_en.strip()} {last_en.strip()}"
                
                # Use the faculty name from the professor's information (if available), otherwise use the faculty name used for the search.
                staff_fac_en = staff.get("Faculty_Name_En") or fac_en

                # Save or Update into DB
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

        self.stdout.write(self.style.SUCCESS(
            f"\nSync Complete!\n"
            f"   - New Authors Added: {total_saved}\n"
            f"   - Existing Authors Updated: {total_updated}"
        ))