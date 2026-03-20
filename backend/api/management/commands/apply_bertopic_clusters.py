import os
import json
import re
from tqdm import tqdm
from django.core.management.base import BaseCommand
from api.models import Paper
from api.services.bertopic_service import BERTopicService 
from api.services.gemini_service import GeminiNamingService

class Command(BaseCommand):
    help = "Run BERTopic, auto-tune, and use Gemini LLM to generate human-readable topic names"

    def add_arguments(self, parser):
        parser.add_argument("--gemini_key", type=str, help="Gemini API Key for auto-naming topics")
        parser.add_argument("--auto_tune", action="store_true", help="Auto-tune the number of topics")

    def handle(self, *args, **options):
        auto_tune = options.get("auto_tune")
        gemini_key = options.get("gemini_key")

        self.stdout.write(self.style.NOTICE("1. Fetching papers from Database..."))
        papers = list(Paper.objects.exclude(abstract__isnull=True).exclude(abstract="").values('id', 'title', 'abstract'))
        
        if not papers:
            self.stdout.write(self.style.ERROR("No papers with abstracts found."))
            return

        docs = [f"{p['title']}. {p['abstract']}" for p in papers]
        paper_ids = [p['id'] for p in papers]

        self.stdout.write(self.style.NOTICE("2. Training BERTopic..."))
        bertopic_service = BERTopicService( #
            n_topics="auto" if auto_tune else None, #
            use_approx_dist=True, #
            use_lemmatized_input=False #
        )
        topics, probs = bertopic_service.fit_transform(docs) #

        self.stdout.write(self.style.NOTICE("3. Assigning LLM Names..."))
        # Gemini Service 
        gemini_service = GeminiNamingService(api_key=gemini_key)
        llm_names = gemini_service.generate_topic_names(bertopic_service.topic_model)

        self.stdout.write(self.style.NOTICE("4. Updating Database..."))
        
        updated_count = 0
        for i, paper_id in enumerate(tqdm(paper_ids, desc="Saving to DB")):
            topic_id = topics[i]
            paper_prob = probs[i] if probs is not None else []
            distribution_list = []

            if len(paper_prob) > 0:
                distribution_list = [float(prob) for prob in paper_prob]

            if topic_id == -1:
                cluster_label = "Outlier / Noise"
            else:
                topic_str_id = str(topic_id)
                if topic_str_id in llm_names:
                    cluster_label = f"Topic {topic_id}: {llm_names[topic_str_id]}"
                else:
                    words = [word for word, _ in bertopic_service.topic_model.get_topic(topic_id)][:5]
                    cluster_label = f"Topic {topic_id}: {', '.join(words)}"

            multi_labels = [cluster_label]
            if topic_id != -1 and len(paper_prob) > 0:
                for alt_topic_id, prob in enumerate(paper_prob):
                    if alt_topic_id != topic_id and prob > 0.15:
                        alt_str_id = str(alt_topic_id)
                        if alt_str_id in llm_names:
                            alt_label = f"Topic {alt_topic_id}: {llm_names[alt_str_id]}"
                        else:
                            alt_words = [word for word, _ in bertopic_service.topic_model.get_topic(alt_topic_id)][:5]
                            alt_label = f"Topic {alt_topic_id}: {', '.join(alt_words)}"
                        multi_labels.append(alt_label)

            raw_keywords = []
            if topic_id != -1:
                raw_keywords = [word for word, _ in bertopic_service.topic_model.get_topic(topic_id)][:10]

            Paper.objects.filter(id=paper_id).update(
                cluster_id=topic_id,
                cluster_label=cluster_label,
                predicted_multi_labels=multi_labels,
                topic_keywords=raw_keywords,
                topic_distribution=distribution_list
            )
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully clustered and updated {updated_count} papers!"))