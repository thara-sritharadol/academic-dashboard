import numpy as np
from collections import Counter
from api.models import Author

class AuthorProfileService:
    
    @staticmethod
    def generate_all_profiles():
        authors = Author.objects.prefetch_related('papers').all()
        updated_count = 0

        for author in authors:
            papers = author.papers.all()
            if not papers:
                continue
            
            update_fields = [] 
            
            # ==========================================
            # 1. Primary Cluster
            # ==========================================
            cluster_ids = [p.cluster_id for p in papers if p.cluster_id is not None]
            
            if cluster_ids:
                valid_clusters = [c for c in cluster_ids if c != -1]
                target_clusters = valid_clusters if valid_clusters else cluster_ids
                
                if target_clusters:
                    most_common_id = Counter(target_clusters).most_common(1)[0][0]
                    author.primary_cluster = str(most_common_id)
                    update_fields.append('primary_cluster')

            # ==========================================
            # 2. Topic Profile
            # ==========================================
            distributions = [p.topic_distribution for p in papers if p.topic_distribution]
            
            if distributions:
                max_len = max(len(d) for d in distributions)
                padded_dists = [d + [0.0] * (max_len - len(d)) for d in distributions]
                avg_dist = np.mean(padded_dists, axis=0)
                
                author.topic_profile = [float(x) for x in avg_dist]
                update_fields.append('topic_profile') 

            # ==========================================
            # Save into Database
            # ==========================================
            if update_fields:
                author.save(update_fields=update_fields)
                updated_count += 1
            
        return {
            "status": "success", 
            "updated": updated_count,
            "message": f"Successfully generated profiles for {updated_count} authors."
        }