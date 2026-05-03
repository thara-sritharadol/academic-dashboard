from django.db.models import Count, Q
from collections import defaultdict
from api.models import Paper, Author, Topic

class AuthorsService:
    TU_INSTITUTION_NAME = "Thammasat University"

    @staticmethod
    def get_author_network(limit=200, domains_param=None):
        papers_query = Paper.objects.prefetch_related('authors').order_by('-year')
        
        if domains_param:
            selected_topics = [d.strip() for d in domains_param.split(',') if d.strip()]
            domain_q = Q(topic_info__primary_topic__name__in=selected_topics)
            
            for topic in selected_topics:
                domain_q |= Q(topic_info__predicted_multi_labels__icontains=topic)
                
            papers = papers_query.filter(domain_q).distinct()[:limit]

        else:
            papers = papers_query[:limit]

        involved_authors = Author.objects.filter(papers__in=papers).distinct().annotate(
            relevant_paper_count=Count('papers', filter=Q(papers__in=papers))
        )
        
        tu_authors = involved_authors.filter(institution=AuthorsService.TU_INSTITUTION_NAME)
        external_authors = involved_authors.exclude(institution=AuthorsService.TU_INSTITUTION_NAME)
        tu_author_ids = set(tu_authors.values_list('id', flat=True))
        
        external_author_tu_collaborator_count = defaultdict(set)
        potential_links = defaultdict(int)
        
        for paper in papers:
            authors = list(paper.authors.all())
            author_ids = [a.id for a in authors]
            
            for i in range(len(author_ids)):
                for j in range(i + 1, len(author_ids)):
                    id1, id2 = sorted([author_ids[i], author_ids[j]])
                    potential_links[f"{id1}-{id2}"] += 1
                    
                    if id1 in tu_author_ids and id2 not in tu_author_ids:
                        external_author_tu_collaborator_count[id2].add(id1)
                    elif id2 in tu_author_ids and id1 not in tu_author_ids:
                        external_author_tu_collaborator_count[id1].add(id2)

        final_nodes_dict = {}
        TU_GROUP_NAME = "Thammasat University"
        
        for author in tu_authors:
            final_nodes_dict[author.id] = {
                "id": str(author.id),
                "name": author.name,
                "val": (author.relevant_paper_count | 1) + 2,
                "group": TU_GROUP_NAME,
                "institution": author.institution,
                "faculty": author.faculty
            }
            
        qualified_external_count = 0
        for author in external_authors:
            tu_friend_count = len(external_author_tu_collaborator_count.get(author.id, set()))
            if tu_friend_count >= 2: 
                final_nodes_dict[author.id] = {
                    "id": str(author.id),
                    "name": author.name,
                    "val": (author.relevant_paper_count | 1) + 2,
                    "group": "External Partner",
                    "institution": author.institution if author.institution else "External"
                }
                qualified_external_count += 1

        final_links = []
        nodes_kept_ids = set(final_nodes_dict.keys())
        for link_key, weight in potential_links.items():
            id1_str, id2_str = link_key.split('-')
            id1, id2 = int(id1_str), int(id2_str)
            if id1 in nodes_kept_ids and id2 in nodes_kept_ids:
                final_links.append({
                    "source": str(id1),
                    "target": str(id2),
                    "weight": weight
                })

        return {
            "nodes": list(final_nodes_dict.values()), 
            "links": final_links,
            "total_external_found": external_authors.count(),
            "qualified_external_count": qualified_external_count
        }
    
    @staticmethod
    def get_top_author(limit=5):
        top_authors = Author.objects.filter(
            institution=AuthorsService.TU_INSTITUTION_NAME
        ).annotate(
            works_count=Count('papers')
        ).order_by('-works_count')[:limit]
        
        return list(top_authors.values('id', 'name', 'works_count', 'faculty'))
    
    @staticmethod
    def get_author_detail(author_id):
        try:
            author = Author.objects.get(id=author_id)
        except Author.DoesNotExist:
            return None

        papers = Paper.objects.filter(authors=author).select_related('topic_info')
        
        all_topics_db = Topic.objects.all()
        topic_dict = {t.topic_id: {"id": t.topic_id, "name": t.name, "keywords": t.keywords} for t in all_topics_db}

        total_citations = 0
        overall_dist = defaultdict(float)
        papers_with_dist_count = 0

        for paper in papers:
            total_citations += paper.citation_count
            if hasattr(paper, 'topic_info') and paper.topic_info and paper.topic_info.topic_distribution:
                dist = paper.topic_info.topic_distribution
                if dist and isinstance(dist, list):
                    for t_id, prob in enumerate(dist):
                        overall_dist[t_id] += prob
                    papers_with_dist_count += 1

        distribution_chart_data = []
        if papers_with_dist_count > 0:
            sorted_dist = sorted(overall_dist.items(), key=lambda x: x[1], reverse=True)
            for t_id, total_prob in sorted_dist[:6]:
                if t_id in topic_dict and total_prob > 0:
                    distribution_chart_data.append({
                        "subject": topic_dict[t_id]["name"],
                        "probability": round(total_prob / papers_with_dist_count, 4),
                        "keywords": topic_dict[t_id]["keywords"]
                    })

        return {
            "id": author.id,
            "openalex_id": author.openalex_id,
            "name": author.name,
            "institution": author.institution,
            "faculty": author.faculty,
            "department": author.department,
            "stats": {
                "total_papers": len(papers),
                "total_citations": total_citations,
            },
            "distribution_chart": distribution_chart_data
        }