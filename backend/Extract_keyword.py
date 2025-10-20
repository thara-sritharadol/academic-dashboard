# -*- coding: utf-8 -*-
from rake_nltk import Rake
from keybert import KeyBERT

# ตัวอย่าง abstract
abstract = """
In an effort to bolster the healthcare system in Thailand, particularly in remote areas with limited access to pharmacists, this study proposes a novel drug recommendation system based on drug details. This system aims to address the challenge of medication selection in resource-constrained settings by providing physicians with informed recommendations tailored to patient needs.The proposed system utilizes drug data sourced from 1mg.com, encompassing approximately 34,284 drug entries. To ensure high-quality recommendations, the data undergoes a rigorous preprocessing phase involving null value imputation and feature extraction using techniques like TF-IDF. Following preprocessing, a combination of Drug Recommendation with cosine similarity and the Bee Algorithm is employed. Cosine similarity establishes a baseline for drug similarity, while the Bee Algorithm optimizes the selection process by considering additional factors beyond just similarity, such as potential side effects and cost-effectiveness.
"""

# ----------------------------
# วิธีที่ 1: ใช้ RAKE (Rapid Automatic Keyword Extraction)
# ----------------------------
rake = Rake()  # ใช้ stopwords และ punctuation จาก nltk
rake.extract_keywords_from_text(abstract)
rake_keywords = rake.get_ranked_phrases()[:10]  # top 10 keywords
print("RAKE Keywords:")
print(rake_keywords)

# ----------------------------
# วิธีที่ 2: ใช้ KeyBERT (BERT-based)
# ----------------------------
kw_model = KeyBERT(model="all-MiniLM-L6-v2")  # ใช้โมเดล lightweight
keybert_keywords = kw_model.extract_keywords(abstract, top_n=10, stop_words='english')
print("\nKeyBERT Keywords:")
print([kw for kw, score in keybert_keywords])
