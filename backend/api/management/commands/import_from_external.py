import json
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Paper, Author

class Command(BaseCommand):
    help = "Import clustering results (BERTopic or NMF) and update Author profiles"

    def add_arguments(self, parser):
        parser.add_argument(
            '--method', 
            type=str, 
            default='bertopic',
            choices=['bertopic', 'nmf'],
            help='Method used for clustering: "bertopic" (default) or "nmf"'
        )

    def handle(self, *args, **options):
        method = options['method']
        
        if method == 'nmf':
            filename = "nmf_overlapping_results.json"
            json_dist_key = "overlapping_clusters"
            score_key = "score"
            print(f"🔄 Mode selected: NMF Overlapping Clustering")
        else:
            filename = "bertopic_results.json"
            json_dist_key = "topic_distribution"
            score_key = "prob"
            print(f"🔄 Mode selected: BERTopic Soft Clustering")

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File '{filename}' not found! Please run the Colab script for {method} first."))
            return

        print(f"Importing results for {len(results)} papers...")

        count = 0
        with transaction.atomic():
            for item in results:
                try:
                    p = Paper.objects.get(id=item['id'])
                    
                    p.cluster_id = item.get('cluster_id')
                    p.cluster_label = item.get('cluster_label')
                    
                    raw_dist = item.get(json_dist_key, [])
                    
                    standardized_dist = []
                    if raw_dist:
                        for d in raw_dist:
                            standardized_dist.append({
                                "topic_id": d.get('topic_id'),
                                "label": d.get('label'),
                                "prob": d.get(score_key, 0)
                            })
                    
                    p.topic_distribution = standardized_dist
                    p.save()
                    count += 1
                except Paper.DoesNotExist:
                    continue
        
        print(f"Updated {count} papers. Now calculating Author Profiles...")

        self._update_author_profiles()

    def _update_author_profiles(self):
        authors = Author.objects.all().prefetch_related('papers')
        updates = []

        print("   > Calculating weighted profiles...")
        
        for author in authors:
            topic_scores = defaultdict(float)
            total_score = 0
            
            papers = author.papers.exclude(topic_distribution__isnull=True)
            if not papers.exists():
                continue

            for p in papers:
                if p.topic_distribution:
                    dist_data = p.topic_distribution
                    if isinstance(dist_data, str):
                        try:
                            dist_data = json.loads(dist_data)
                        except:
                            continue

                    for topic in dist_data:
                        label = topic.get('label')
                        prob = topic.get('prob', 0)
                        
                        if label and prob > 0:
                            topic_scores[label] += prob
                            total_score += prob
            
            if total_score == 0:
                continue

            final_profile = {}
            for label, score in topic_scores.items():
                if label != "Outlier / Uncategorized" and label != "Uncategorized": 
                    final_profile[label] = round(score / total_score, 4)

            if final_profile:
                primary_cluster = max(final_profile, key=final_profile.get)
            else:
                primary_cluster = "Uncategorized"

            author.primary_cluster = primary_cluster
            author.topic_profile = final_profile
            updates.append(author)

        if updates:
            Author.objects.bulk_update(updates, ['primary_cluster', 'topic_profile'])
            self.stdout.write(self.style.SUCCESS(f"Successfully updated profiles for {len(updates)} authors!"))
        else:
            self.stdout.write(self.style.WARNING("No authors needed updating."))