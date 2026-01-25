import os
import django
import sys
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# ---------------------------------------------------------
# 1. SETUP DJANGO ENVIRONMENT
# ---------------------------------------------------------
# ตั้งค่าให้ Python รู้จัก Django Project ของคุณ
# เปลี่ยน 'backend.settings' เป็นชื่อ folder project คุณถ้าไม่ตรงกัน
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings') 
django.setup()

# Import Model หลังจาก setup django แล้วเท่านั้น
from api.models import Paper

# ---------------------------------------------------------
# 2. CONFIGURATION
# ---------------------------------------------------------
MAX_K = 15  # จำนวนกลุ่มสูงสุดที่จะทดสอบ
MIN_PAPER_COUNT = 20 # จำนวน paper ขั้นต่ำที่ต้องมีถึงจะเริ่มทำงาน

# ---------------------------------------------------------
# 3. MAIN LOGIC
# ---------------------------------------------------------
def run_analysis():
    print("Fetching abstracts from database...")
    
    # ดึงเฉพาะ Abstract ที่ไม่ว่าง (Not Null และ Not Empty)
    papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract__exact='')
    abstracts = list(papers.values_list('abstract', flat=True))
    
    count = len(abstracts)
    print(f"Found {count} papers with abstracts.")

    if count < MIN_PAPER_COUNT:
        print(f"Error: Not enough data. You need at least {MIN_PAPER_COUNT} abstracts to run clustering.")
        return

    # --- Preprocessing & Vectorization ---
    print("Vectorizing text (TF-IDF)...")
    
    # เพิ่มคำขยะทางวิชาการ (Stopwords) ที่มักจะทำให้การแบ่งกลุ่มเพี้ยน
    academic_stopwords = [
        'paper', 'study', 'research', 'proposed', 'method', 'result', 
        'analysis', 'based', 'using', 'approach', 'algorithm', 'system',
        'model', 'data', 'performance', 'application', 'new', 'development'
    ]
    
    vectorizer = TfidfVectorizer(
        stop_words='english',      # ลบคำทั่วไป (a, an, the)
        max_features=1000,         # เอาแค่ 1000 คำสำคัญ
        max_df=0.9,                # ตัดคำที่โผล่ในเอกสารเกิน 90% (คำเฟ้อ)
        min_df=2                   # ตัดคำที่โผล่ไม่ถึง 2 เอกสาร (คำเฉพาะเกินไป)
    )
    
    # update stopwords
    current_stops = list(vectorizer.get_stop_words() or [])
    vectorizer.stop_words_ = current_stops + academic_stopwords

    try:
        X = vectorizer.fit_transform(abstracts)
    except ValueError as e:
        print(f"Error during vectorization: {e}")
        return

    # --- Loop Finding K ---
    inertias = []
    silhouette_scores = []
    k_range = range(2, min(MAX_K + 1, count)) # K ต้องไม่เกินจำนวนเอกสาร

    print(f"Calculating metrics for K=2 to {MAX_K}...")
    
    for k in k_range:
        # n_init=10: รันสุ่ม 10 รอบแล้วเลือกผลดีสุด (มาตรฐาน)
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        
        # 1. Elbow Method (Inertia)
        inertias.append(kmeans.inertia_)
        
        # 2. Silhouette Score
        try:
            score = silhouette_score(X, kmeans.labels_)
        except Exception:
            score = 0
        silhouette_scores.append(score)
        
        print(f"   > K={k}: Silhouette={score:.4f}, Inertia={kmeans.inertia_:.0f}")

    # --- Visualization ---
    print("Plotting graphs...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Graph 1: Elbow
    ax1.plot(k_range, inertias, 'bo-', markersize=8)
    ax1.set_xlabel('Number of Clusters (k)')
    ax1.set_ylabel('Inertia (Lower is better)')
    ax1.set_title('Elbow Method')
    ax1.grid(True)

    # Graph 2: Silhouette
    ax2.plot(k_range, silhouette_scores, 'ro-', markersize=8)
    ax2.set_xlabel('Number of Clusters (k)')
    ax2.set_ylabel('Silhouette Score (Higher is better)')
    ax2.set_title('Silhouette Analysis')
    ax2.grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_analysis()