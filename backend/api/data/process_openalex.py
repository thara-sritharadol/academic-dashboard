import os
import gzip
import json
import pandas as pd
from tqdm import tqdm

def process_openalex_concepts_to_csv(data_directory, output_csv_path):
    """
    Reads all .gz files in a directory and all its subdirectories, 
    extracts concept data, and saves it to a single CSV file.
    """
    all_files = []
    # ## CHANGED ##: เปลี่ยนมาใช้ os.walk เพื่อค้นหาไฟล์ในโฟลเดอร์ย่อยทั้งหมด
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
                    level = record.get('level')
                    
                    if topic_name:
                        if not description:
                            description = f"The field of study related to {topic_name}."
                        
                        topics_data.append({
                            'topic_name': topic_name,
                            'topic_description': description,
                            'level': level
                        })
        except Exception as e:
            print(f"Could not process file {file_path}: {e}")

    if not topics_data:
        print("No topic data could be extracted.")
        return

    print(f"Extracted {len(topics_data):,} topics. Creating CSV...")
    
    df = pd.DataFrame(topics_data)
    df_final = df[['topic_name', 'topic_description']]
    df_final.to_csv(output_csv_path, index=False)
    
    print(f"✅ Successfully created '{output_csv_path}'")

if __name__ == '__main__':
    # ไม่ต้องแก้ไขส่วนนี้
    DATA_DIR = 'concepts' 
    OUTPUT_FILE = 'fos_topics.csv'
    
    process_openalex_concepts_to_csv(DATA_DIR, OUTPUT_FILE)