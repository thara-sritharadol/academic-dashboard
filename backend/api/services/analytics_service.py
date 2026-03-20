from django.db.models import Count, Q
from collections import defaultdict
from api.models import Paper, Author

class AnalyticsService:
    TU_INSTITUTION_NAME = "Thammasat University"

    @staticmethod
    def get_dashboard_summary():
        return {
            'total_papers': Paper.objects.count(),
            'total_authors': Author.objects.count(),
            'total_clusters': Paper.objects.exclude(cluster_label__isnull=True).values('cluster_label').distinct().count()
        }

    @staticmethod
    def get_domain_trends():
        papers = Paper.objects.exclude(year__isnull=True).exclude(cluster_label__isnull=True)
        data = papers.values('year', 'cluster_label').annotate(count=Count('id')).order_by('year')
        
        trend_dict = defaultdict(dict)
        for item in data:
            y = item['year']
            lbl = item['cluster_label']
            trend_dict[y]['year'] = str(y)
            trend_dict[y][lbl] = item['count']
            
        return list(trend_dict.values())

    @staticmethod
    def get_all_topics():
        topics = Paper.objects.exclude(cluster_label__isnull=True).values_list('cluster_label', flat=True).distinct()
        topic_list = [t for t in topics if t != "Outlier / Noise"]
        return sorted(topic_list)

    @staticmethod
    def get_author_network(limit=200, domains_param=None):
        papers_query = Paper.objects.prefetch_related('authors').order_by('-year')
        
        if domains_param:
            selected_prefixes = [d.split(':')[0].strip() for d in domains_param.split(',')]
            query = Q()
            for prefix in selected_prefixes:
                search_term = f'"{prefix}:'
                query |= Q(predicted_multi_labels__icontains=search_term)
            papers = papers_query.filter(query)[:limit]
        else:
            papers = papers_query[:limit]

        # Pull up the list of all professors involved in this series of papers.
        involved_authors = Author.objects.filter(papers__in=papers).distinct().annotate(
            relevant_paper_count=Count('papers', filter=Q(papers__in=papers))
        )
        
        tu_authors = involved_authors.filter(institution=AnalyticsService.TU_INSTITUTION_NAME)
        external_authors = involved_authors.exclude(institution=AnalyticsService.TU_INSTITUTION_NAME)
        tu_author_ids = set(tu_authors.values_list('id', flat=True))
        
        external_author_tu_collaborator_count = defaultdict(set)
        potential_links = defaultdict(int)
        
        # Looping to find the co-authorship relationship.
        for paper in papers:
            authors = list(paper.authors.all())
            author_ids = [a.id for a in authors]
            
            for i in range(len(author_ids)):
                for j in range(i + 1, len(author_ids)):
                    id1, id2 = sorted([author_ids[i], author_ids[j]])
                    potential_links[f"{id1}-{id2}"] += 1
                    
                    # Records of outsiders working with people inside TU.
                    if id1 in tu_author_ids and id2 not in tu_author_ids:
                        external_author_tu_collaborator_count[id2].add(id1)
                    elif id2 in tu_author_ids and id1 not in tu_author_ids:
                        external_author_tu_collaborator_count[id1].add(id2)

        final_nodes_dict = {}
        TU_GROUP_NAME = "Thammasat University"
        
        # Add people nodes to all TUs.
        for author in tu_authors:
            final_nodes_dict[author.id] = {
                "id": str(author.id),
                "name": author.name,
                "val": (author.relevant_paper_count | 1) + 2,
                "group": TU_GROUP_NAME,
                "institution": author.institution,
                "faculty": author.faculty
            }
            
        # Add an external node (one that has previously co-authored with at least two people within TU).
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

        # Create specific connections between selected nodes.
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