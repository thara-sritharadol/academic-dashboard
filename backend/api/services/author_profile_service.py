import numpy as np
from collections import Counter
from api.models import Author

class AuthorProfileService:
    
    @staticmethod
    def generate_all_profiles():
        # Pull in all professors along with the paper data to reduce N+1 queries.
        authors = Author.objects.prefetch_related('papers').all()
        updated_count = 0

        for author in authors:
            papers = author.papers.all()
            if not papers:
                continue
            
            # ==========================================
            # Primary Cluster (Most frequently published topics)
            # ==========================================
            cluster_ids = [p.cluster_id for p in papers if p.cluster_id is not None]
            
            if cluster_ids:
                # Try to avoid Outlier (-1) if possible.
                valid_clusters = [c for c in cluster_ids if c != -1]
                # If all papers are outliers, then we're forced to use -1.
                target_clusters = valid_clusters if valid_clusters else cluster_ids
                
                if target_clusters:
                    # Find the ID with the most duplicates.
                    most_common_id = Counter(target_clusters).most_common(1)[0][0]
                    author.primary_cluster = str(most_common_id)

            # ==========================================
            # Topic Profile (Average proportion of topics)
            # ==========================================
            distributions = [p.topic_distribution for p in papers if p.topic_distribution]
            
            if distributions:
                # Calculate the length of the array(usually equal to the total number of topics).
                max_len = max(len(d) for d in distributions)
                
                # If an array element is shorter than normal, add zeros to the end (padding).
                padded_dists = [d + [0.0] * (max_len - len(d)) for d in distributions]
                
                # Use Numpy to find the mean of each column (axis=0) in one go.
                avg_dist = np.mean(padded_dists, axis=0)
                
                # Convert a Numpy Float back to a regular Python Float for saving to a JSON Field.
                author.topic_profile = [float(x) for x in avg_dist]

            # Save into Database
            update_fields = []
            if hasattr(author, 'primary_cluster'): update_fields.append('primary_cluster')
            if hasattr(author, 'topic_profile'): update_fields.append('topic_profile')
            
            if update_fields:
                author.save(update_fields=update_fields)
                updated_count += 1
            
        return {
            "status": "success", 
            "updated": updated_count,
            "message": f"Successfully generated profiles for {updated_count} authors."
        }