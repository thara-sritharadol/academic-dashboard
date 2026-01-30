import os
import django
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Author

def find_potential_duplicates():

    authors = Author.objects.all()
    
    last_name_map = defaultdict(list)
    
    print("Scanning for potential duplicates...")
    
    for auth in authors:
        parts = auth.name.split()
        if len(parts) > 1:
            last_name = parts[-1].lower()
            if len(last_name) > 3: 
                last_name_map[last_name].append(auth)

    for lname, group in last_name_map.items():
        if len(group) > 1:
            print(f"\nPotential duplicates for surname '{lname.upper()}':")
            for a in group:
                print(f"   - {a.name} (ID: {a.openalex_id}) - {a.papers.count()} papers")

if __name__ == "__main__":
    find_potential_duplicates()