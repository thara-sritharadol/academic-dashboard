import os
import gzip
import json
import pandas as pd
from tqdm import tqdm

# เพิ่มพารามิเตอร์ max_level เข้ามา
def process_openalex_concepts_to_csv(data_directory, output_csv_path, max_level=None):
    """
    Reads all .gz files in a directory and its subdirectories, 
    extracts concept data, (NEW) filters by level, 
    and saves it to a single CSV file.
    """
    all_files = []
    print(f"Searching for .gz files in '{data_directory}' and its subdirectories...")
    for root, dirs, files in os.walk(data_directory):
        for filename in files:
            if filename.endswith('.gz'):
                all_files.append(os.path.join(root, filename))

    if not all_files:
        print(f"Error: No .gz files found in '{data_directory}'")
        return

    print(f"Found {len(all_files)} files to process.")
    
    topics_data = []
    
    for file_path in tqdm(all_files, desc="Processing files"):
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line)
                    
                    topic_name = record.get('display_name')
                    description = record.get('description')
                    level = record.get('level') # ดึง level
                    
                    if topic_name:
                        if not description:
                            description = f"The field of study related to {topic_name}."
                        
                        topics_data.append({
                            'topic_name': topic_name,
                            'topic_description': description,
                            'level': level # เก็บ level ไว้ด้วย
                        })
        except Exception as e:
            print(f"Could not process file {file_path}: {e}")

    if not topics_data:
        print("No topic data could be extracted.")
        return

    print(f"Extracted {len(topics_data):,} total topics.")
    
    df = pd.DataFrame(topics_data)
    
    # --- ## ⚠️ NEW: FILTERING LOGIC ## ---
    # นี่คือส่วนที่เพิ่มเข้ามา
    if max_level is not None:
        print(f"Filtering topics to include only Level <= {max_level}...")
        
        # แปลง 'level' เป็นตัวเลข, หากมีปัญหา (เช่น None) ให้ข้ามไป
        df['level'] = pd.to_numeric(df['level'], errors='coerce')
        df = df.dropna(subset=['level']) # ลบแถวที่ 'level' เป็น None
        df['level'] = df['level'].astype(int)
        
        df_filtered = df[df['level'] <= max_level].copy()
        print(f"Filtered topics: {len(df_filtered):,}")
    else:
        print("No level filtering applied.")
        df_filtered = df.copy()
    # --- ## END OF NEW LOGIC ## ---

    # บันทึกเฉพาะ 2 คอลัมน์ที่จำเป็น (จาก df_filtered)
    df_final = df_filtered[['topic_name', 'topic_description']]
    df_final.to_csv(output_csv_path, index=False)
    
    print(f"✅ Successfully created '{output_csv_path}'")

if __name__ == '__main__':
    DATA_DIR = 'concepts' 
    
    # --- ## ⚙️ CHANGED SETTINGS ## ---
    # ตั้งค่าให้กรองเฉพาะ Level 0 และ 1
    MAX_LEVEL_TO_INCLUDE = 0 
    
    # ตั้งชื่อไฟล์ Output ให้อัตโนมัติ
    OUTPUT_FILE = f'fos_topics_L0-L{MAX_LEVEL_TO_INCLUDE}.csv'
    
    # ส่งค่า max_level เข้าไปในฟังก์ชัน
    process_openalex_concepts_to_csv(DATA_DIR, OUTPUT_FILE, max_level=MAX_LEVEL_TO_INCLUDE)