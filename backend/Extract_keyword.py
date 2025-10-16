# -*- coding: utf-8 -*-
from rake_nltk import Rake
from keybert import KeyBERT

# ตัวอย่าง abstract
abstract = """
Large-scale distributed systems have become an essential part of our everyday life. These systems have a large number of hardware and software components, often cooperating in complex and unpredictable ways. Operating these kinds of systems requires centralized monitoring to understand their overall states. While running software to collect metrics in a server is considered common nowadays, it often goes unstudied the impact metric collection software have on the base system. This is especially important in low-power, IoT applications. According to our review, one particular software, Telegraf, has never been formally studied before in terms of how much overhead Telegraf adds to the base system. In this work, we conducted several experiments to study how the base system is affected by Telegraf in two scenarios: a datacenter server and an IoT node. The results show that Telegraf is lightweight and suitable to serve as a real-time monitoring agent in both scenarios.
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
kw_model = KeyBERT(model="all-mpnet-base-v2")  # ใช้โมเดล lightweight
keybert_keywords = kw_model.extract_keywords(abstract, top_n=10, stop_words='english')
print("\nKeyBERT Keywords:")
print([kw for kw, score in keybert_keywords])
