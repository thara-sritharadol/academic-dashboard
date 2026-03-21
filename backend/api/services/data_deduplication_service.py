from django.db.models import Count
from django.db.models.functions import Lower
from api.models import Author, Paper

class DataDeduplicationService:
    
    @staticmethod
    def merge_duplicate_authors():
        duplicates = (
            Author.objects.annotate(name_lower=Lower('name'))
            .values('name_lower')
            .annotate(name_count=Count('id'))
            .filter(name_count__gt=1)
        )

        if not duplicates:
            return {"status": "success", "merged": 0, "deleted": 0, "message": "No duplicate authors found."}

        total_merged = 0
        total_deleted = 0

        for dup in duplicates:
            name_lower = dup['name_lower']
            matching_authors = list(Author.objects.filter(name__iexact=name_lower).order_by('-faculty'))
            
            primary_author = matching_authors[0]
            duplicates_to_merge = matching_authors[1:]
            
            for duplicate in duplicates_to_merge:
                for paper in duplicate.papers.all():
                    paper.authors.add(primary_author)
                    paper.authors.remove(duplicate)
                
                if duplicate.openalex_id and not primary_author.openalex_id:
                    primary_author.openalex_id = duplicate.openalex_id
                    primary_author.save()

                duplicate.delete()
                total_deleted += 1
                
            total_merged += 1

        return {
            "status": "success", 
            "merged": total_merged, 
            "deleted": total_deleted,
            "message": f"Merged {total_merged} unique names. Deleted {total_deleted} duplicates."
        }

    @staticmethod
    def merge_duplicate_papers():
        duplicates = (
            Paper.objects.annotate(title_lower=Lower('title'))
            .values('title_lower')
            .annotate(paper_count=Count('id'))
            .filter(paper_count__gt=1)
        )

        if not duplicates:
            return {"status": "success", "merged": 0, "deleted": 0, "message": "No duplicate papers found."}

        total_merged = 0
        total_deleted = 0

        for dup in duplicates:
            title_lower = dup['title_lower']
            matching_papers = list(Paper.objects.filter(title__iexact=title_lower).order_by('-citation_count'))
            
            if len(matching_papers) < 2:
                continue

            primary_paper = matching_papers[0]
            duplicates_to_merge = matching_papers[1:]

            for duplicate in duplicates_to_merge:
                for author in duplicate.authors.all():
                    primary_paper.authors.add(author)
                
                if duplicate.abstract and not primary_paper.abstract:
                    primary_paper.abstract = duplicate.abstract
                
                if duplicate.cluster_id and not primary_paper.cluster_id:
                    primary_paper.cluster_id = duplicate.cluster_id
                    primary_paper.cluster_label = duplicate.cluster_label
                    primary_paper.predicted_multi_labels = duplicate.predicted_multi_labels
                    primary_paper.topic_keywords = duplicate.topic_keywords
                    primary_paper.topic_distribution = duplicate.topic_distribution

                primary_paper.save()
                duplicate.delete()
                total_deleted += 1
            
            total_merged += 1

        return {
            "status": "success", 
            "merged": total_merged, 
            "deleted": total_deleted,
            "message": f"Processed {total_merged} duplicate groups. Removed {total_deleted} redundant papers."
        }