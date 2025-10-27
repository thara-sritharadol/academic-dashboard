import os
import gzip
import json
import pandas as pd
from tqdm import tqdm

def create_hierarchy_and_level_maps(data_directory, hierarchy_output_path, level_output_path):
    """
    Reads all .gz files, extracts ancestor data AND level data,
    and saves them to two separate JSON map files.
    """
    all_files = []
    print(f"🔍 Searching for .gz files in '{data_directory}'...")
    for root, dirs, files in os.walk(data_directory):
        for filename in files:
            if filename.endswith('.gz'):
                all_files.append(os.path.join(root, filename))

    if not all_files:
        print(f"Error: No .gz files found in '{data_directory}'")
        return

    print(f"Found {len(all_files)} files to process.")
    
    hierarchy_map = {}
    level_map = {} # <-- 1. สร้าง Dictionary เปล่าสำหรับ Level Map
    
    for file_path in tqdm(all_files, desc="Processing files"):
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line)
                    
                    topic_name = record.get('display_name')
                    level = record.get('level') # <-- 2. ดึง Level ออกมา
                    ancestors = record.get('ancestors')
                    
                    if not topic_name:
                        continue
                        
                    # 3. บันทึก Level ของ Topic นี้
                    if level is not None:
                        level_map[topic_name] = level
                        
                    # 4. บันทึก Hierarchy (เหมือนเดิม)
                    if ancestors:
                        ancestor_names = [
                            ancestor['display_name'] 
                            for ancestor in ancestors 
                            if 'display_name' in ancestor
                        ]
                        if ancestor_names:
                            hierarchy_map[topic_name] = ancestor_names
                            
        except Exception as e:
            print(f"Could not process file {file_path}: {e}")

    # --- บันทึกไฟล์ Hierarchy Map (เหมือนเดิม) ---
    if hierarchy_map:
        print(f"\nExtracted {len(hierarchy_map):,} topics with ancestor data.")
        print(f"💾 Saving hierarchy map to '{hierarchy_output_path}'...")
        with open(hierarchy_output_path, 'w', encoding='utf-8') as f:
            json.dump(hierarchy_map, f, indent=2, ensure_ascii=False)
        print(f"✅ Created '{hierarchy_output_path}'")
    else:
        print("No hierarchy data could be extracted.")
        
    # --- 5. บันทึกไฟล์ Level Map (ใหม่) ---
    if level_map:
        print(f"\nExtracted {len(level_map):,} topics with level data.")
        print(f"💾 Saving level map to '{level_output_path}'...")
        with open(level_output_path, 'w', encoding='utf-8') as f:
            json.dump(level_map, f, indent=2, ensure_ascii=False)
        print(f"✅ Created '{level_output_path}'")
    else:
        print("No level data could be extracted.")

if __name__ == '__main__':
    DATA_DIR = 'concepts' 
    HIERARCHY_FILE = 'fos_hierarchy_map.json'
    LEVEL_FILE = 'fos_level_map.json' # <-- ชื่อไฟล์ใหม่
    
    create_hierarchy_and_level_maps(DATA_DIR, HIERARCHY_FILE, LEVEL_FILE)