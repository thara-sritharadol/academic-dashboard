import os
from prefect import flow, task, get_run_logger
from tu_sync_authors import run_find_researcher
from fetch_papers import run_fetch_papers
from process_clean_papers import run_clean_papers
from process_deduplicate import run_deduplicate
from run_bertopic_pipeline import run_cluster
from load_s3_to_db_pure import load_to_db

# ==========================================
# 1. สร้าง Tasks สำหรับแต่ละขั้นตอน
# ==========================================

@task(name="1. Sync TU Authors", retries=2, retry_delay_seconds=30)
def task_sync_authors(faculty=None):
    logger = get_run_logger()
    logger.info(f"เริ่มดึงข้อมูลรายชื่ออาจารย์ (Faculty: {faculty if faculty else 'All'})...")
    
    # สคริปต์ของคุณใช้ event, context
    result = run_find_researcher({"faculty": faculty}, None)
    
    if result.get("status") == "error":
        logger.error(f"Sync Authors Failed: {result.get('message')}")
        raise Exception(f"Task Failed: {result.get('message')}")
        
    logger.info(f"ดึงข้อมูลอาจารย์สำเร็จ: {result.get('saved_count')} รายการ")

@task(name="2. Fetch Papers from OpenAlex", retries=2, retry_delay_seconds=60)
def task_fetch_papers(limit=None, source="local"):
    logger = get_run_logger()
    logger.info(f"เริ่มดึงข้อมูลบทความ (Limit: {limit}, Source: {source})...")
    run_fetch_papers(author_limit=limit, source_type=source)
    logger.info("ดึงข้อมูลบทความเสร็จสิ้น")

@task(name="3. Clean Papers Data")
def task_clean_papers(source="local"):
    logger = get_run_logger()
    logger.info(f"เริ่มทำความสะอาดข้อมูล (Source: {source})...")
    run_clean_papers(source_type=source)
    logger.info("ทำความสะอาดข้อมูลเสร็จสิ้น")

@task(name="4. Deduplicate Papers")
def task_deduplicate_papers(source="local"):
    logger = get_run_logger()
    logger.info(f"เริ่มกระบวนการลบข้อมูลซ้ำ (Source: {source})...")
    run_deduplicate(source_type=source)
    logger.info("ลบข้อมูลซ้ำเสร็จสิ้น")

@task(name="5. Run BERTopic Modeling")
def task_run_bertopic(source="local"):
    logger = get_run_logger()
    logger.info(f"เริ่มประมวลผล Topic Modeling & LLM Naming (Source: {source})...")
    run_cluster(source_type=source)
    logger.info("ประมวลผล Topic Modeling เสร็จสิ้น")

@task(name="6. Load Data to Database")
def task_load_to_db(source="local"):
    logger = get_run_logger()
    logger.info(f"เริ่มโหลดข้อมูลและสถิติทั้งหมดลง Database (Source: {source})...")
    load_to_db(source_type=source)
    logger.info("โหลดข้อมูลลง Database สำเร็จ!")

# ==========================================
# 2. สร้าง Flow หลักเพื่อผูก Tasks เข้าด้วยกัน
# ==========================================

@flow(name="TU Research Network ETL Pipeline", description="Pipeline ดึงข้อมูล จัดการซ้ำ จัดกลุ่ม และโหลดลง DB")
def end_to_end_pipeline(
    source_type: str = "local", 
    author_limit: int = None, 
    specific_faculty: str = None
):
    logger = get_run_logger()
    logger.info("Starting End-to-End Research Pipeline...")
    logger.info(f"Config: Source={source_type}, Limit={author_limit}, Faculty={specific_faculty}")

    try:
        # การเรียกฟังก์ชัน Task ต่อกันใน Flow จะทำงานแบบ Sequential (รอให้เสร็จทีละสเตป) โดยอัตโนมัติ
        task_sync_authors(faculty=specific_faculty)
        
        task_fetch_papers(limit=author_limit, source=source_type)
        
        task_clean_papers(source=source_type)
        
        task_deduplicate_papers(source=source_type)
        
        task_run_bertopic(source=source_type)
        
        task_load_to_db(source=source_type)

        logger.info("Pipeline completed successfully!")
        
    except Exception as e:
        logger.error(f"Pipeline failed during execution: {e}")
        raise e

# ==========================================
# 3. จุดเริ่มต้นการทำงาน (Entrypoint)
# ==========================================
if __name__ == "__main__":
    # คุณสามารถเปลี่ยนพารามิเตอร์ตรงนี้ได้ตามต้องการเวลาทดสอบรันด้วย python main_pipeline.py
    end_to_end_pipeline(
        source_type="local",    # หรือ "s3"
        author_limit=10,      # ใส่ตัวเลขเช่น 10 เพื่อเทสต์ระบบ
        specific_faculty="Faculty of Science and Technology"
    )