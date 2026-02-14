from django.core.management.base import BaseCommand
from api.services.clustering_service import ClusteringService
import pandas as pd

class Command(BaseCommand):
    help = 'Run BERTopic clustering pipeline via Service Layer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting Clustering Pipeline...'))

        try:
            #Initialize Service
            service = ClusteringService()
            
            #Load Data
            self.stdout.write("Loading data...")
            if not service.load_data():
                self.stdout.write(self.style.ERROR("No data found."))
                return

            #Perform Clustering
            self.stdout.write("Training model...")
            service.perform_clustering()

            #Evaluate
            self.stdout.write("Evaluating model...")
            metrics = service.evaluate_model()
            
            #Report Output
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f" OVERALL METRICS")
            self.stdout.write("="*50)
            
            #Show Entropy
            mean_ent = metrics['system_entropy']
            self.stdout.write(f" 1. Mean Entropy    : {mean_ent:.4f}")
            
            #translate the Entropy results
            if mean_ent < 0.5:
                self.stdout.write("    -> Interpretation: Highly Specialized (Most papers focus on single topics)")
            elif mean_ent < 1.5:
                self.stdout.write("    -> Interpretation: Hybrid/Interdisciplinary (Good mix of distinct and overlapping topics)")
            else:
                self.stdout.write("    -> Interpretation: Broad/General (Topics are very fuzzy or overlapping)")

            self.stdout.write(f" 2. Coherence (c_v) : {metrics['mean_coherence']:.4f}")
            self.stdout.write(f" 3. Diversity       : {metrics['diversity_score']:.4f}")
            
            #Show details by topic.
            self.stdout.write("\n" + "-"*50)
            self.stdout.write(f" DETAILED COHERENCE PER TOPIC")
            self.stdout.write("-"*50)
            
            if metrics['detailed_coherence']:
                df_details = pd.DataFrame(metrics['detailed_coherence'])
                df_details = df_details.sort_values('coherence_score')
                self.stdout.write(df_details.to_string(index=False))
            else:
                self.stdout.write("No topics found.")

            self.stdout.write("="*50 + "\n")

            #Save Results
            self.stdout.write("Saving results to database...")
            count = service.save_results()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully processed and saved {count} papers.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
            import traceback
            traceback.print_exc()