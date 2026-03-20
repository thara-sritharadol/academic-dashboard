import json
from collections import Counter
from django.core.management.base import BaseCommand
from api.models import Paper

class Command(BaseCommand):
    help = 'Explore and count True Labels distribution in the dataset including intersections'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, help='Path to JSON dataset (optional)')
        parser.add_argument('--threshold', type=float, default=0.3, help='Score threshold for multi-labels')
        parser.add_argument('--target_level', type=int, choices=[0, 1, 2], default=1, help='Target concept level')

    def handle(self, *args, **options):
        input_file = options.get('input')
        threshold = options.get('threshold')
        target_level = options.get('target_level')

        all_true_labels = []
        total_papers = 0
        papers_without_labels = 0

        target_key_hard = f'true_label_l{target_level}'
        target_key_multi = f'multi_labels_l{target_level}'

        self.stdout.write(self.style.NOTICE(f"Exploring Dataset (Target Level: {target_level}, Threshold: {threshold})..."))

        if input_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                true_labels_set = set()
                top_label = item.get(target_key_hard)

                if target_key_multi in item and isinstance(item[target_key_multi], list):
                    true_labels_set = set(item[target_key_multi])
                elif 'openalex_concepts' in item:
                    valid_concepts = [c for c in item['openalex_concepts'] if c.get('level') == target_level and c.get('score', 0) >= threshold]
                    true_labels_set.update([c['name'] for c in valid_concepts])
                    if valid_concepts and not top_label:
                        valid_concepts.sort(key=lambda x: x.get('score', 0), reverse=True)
                        top_label = valid_concepts[0]['name']
                else:
                    if top_label:
                        true_labels_set.add(top_label)

                if true_labels_set:
                    combo_label = " + ".join(sorted(list(true_labels_set)))
                    all_true_labels.append(combo_label)
                    total_papers += 1
                else:
                    papers_without_labels += 1

        else:
            papers = Paper.objects.exclude(abstract__isnull=True).exclude(abstract__exact='')
            for paper in papers:
                concepts = paper.openalex_concepts
                if not isinstance(concepts, list):
                    papers_without_labels += 1
                    continue
                    
                true_labels_set = set()
                valid_concepts = [c for c in concepts if isinstance(c, dict) and c.get('level') == target_level and c.get('score', 0) >= threshold]
                true_labels_set.update([c['name'] for c in valid_concepts])
                
                if true_labels_set:
                    combo_label = " + ".join(sorted(list(true_labels_set)))
                    all_true_labels.append(combo_label)
                    total_papers += 1
                else:
                    papers_without_labels += 1

        label_counts = Counter(all_true_labels)
        total_classes = len(label_counts)

        print("\n" + "="*80)
        print("DATASET LABEL DISTRIBUTION (EDA) - INTERSECTION COUNT")
        print("="*80)
        print(f"Total Papers Processed   : {total_papers + papers_without_labels}")
        print(f"Papers with valid labels : {total_papers}")
        print(f"Papers skipped (No label): {papers_without_labels}")
        print(f"Total Unique Classes     : {total_classes} classes (including combinations)")
        print("-" * 80)
        print(f"{'Rank':<5} | {'Class Name (True Label Combinations)':<50} | {'Count':<10}")
        print("-" * 80)
        
        for i, (label, count) in enumerate(label_counts.most_common()):
            print(f"{i+1:<5} | {label:<50} | {count:<10}")
        
        print("="*80)