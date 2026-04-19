import os
import time
import sys
from prefect import flow, task
import django
from typing import Optional
from django.core.management import call_command
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

@task(name="Fetch & Sync Authors", retries=2, retry_delay_seconds=10)
def fetch_authors(tu_api_key: str, faculty: str):
    call_command('sync_tu_authors', api_key=tu_api_key, faculty=faculty)

@task(name="Fetch Papers", retries=2)
def fetch_papers(batch_size: int, faculty: str):
    call_command('batch_fetch_papers', batch_size=batch_size, faculty=faculty)

@task(name="Clean Texts")
def clean_texts():
    call_command('clean_texts')

@task(name="Deduplicate Data")
def deduplicate_data():
    call_command('merge_authors')
    call_command('merge_papers')

@task(name="BERTopic & Gemini Clustering")
def run_clustering(gemini_key: str, auto_tune: bool):
    if gemini_key:
        call_command('apply_bertopic_clusters', gemini_key=gemini_key, auto_tune=auto_tune)
    else:
        call_command('apply_bertopic_clusters')

@task(name="Generate Author Profiles")
def generate_profiles():
    call_command('generate_author_profiles')

# Flow
@flow(name="Daily Academic Data Pipeline", log_prints=True)
def academic_pipeline_flow(
    tu_api_key: Optional[str] = None,
    faculty: str = "Faculty of Science and Technology", 
    gemini_key: Optional[str] = None,
    batch_size: int = 10, 
    auto_tune: bool = True
):
    # Environment Variables
    tu_api_key = tu_api_key or os.getenv('TU_API_KEY')
    gemini_key = gemini_key or os.getenv('GEMINI_API_KEY')

    if not tu_api_key:
        print("Error: TU API Key is required to run the pipeline.")
        return

    print("=== Starting Daily Data Pipeline with Prefect ===")
    start_time = time.time()

    # Tasks
    fetch_authors(tu_api_key, faculty)
    fetch_papers(batch_size, faculty)
    clean_texts()
    deduplicate_data()
    run_clustering(gemini_key, auto_tune)
    generate_profiles()

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"=== Pipeline Completed Successfully in {int(minutes)}m {int(seconds)}s! ===")

if __name__ == "__main__":
    academic_pipeline_flow()