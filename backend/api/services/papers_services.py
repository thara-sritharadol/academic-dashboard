from django.db.models import Q
from api.models import Paper, Topic
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class PapersService:
    TU_INSTITUTION_NAME = "Thammasat University"

    @staticmethod
    def get_paper_cards(page=1, page_size=12, domains_param=None, search_query=None, author_id=None):
        papers_query = Paper.objects.select_related('topic_info').prefetch_related('authors')

        if author_id:
            papers_query = papers_query.filter(authors__id=author_id)
        
        if domains_param:
            selected_topics = [d.strip() for d in domains_param.split(',') if d.strip()]
            
            domain_q = Q(topic_info__primary_topic__name__in=selected_topics)
            
            for topic in selected_topics:
                domain_q |= Q(topic_info__predicted_multi_labels__icontains=topic)
            
            papers_query = papers_query.filter(domain_q).distinct()

        if search_query:
            papers_query = papers_query.filter(
                Q(title__icontains=search_query) | 
                Q(authors__name__icontains=search_query)
            ).distinct()

        papers_query = papers_query.order_by('-year', '-citation_count')

        paginator = Paginator(papers_query, page_size)
        try:
            papers_page = paginator.page(page)
        except PageNotAnInteger:
            papers_page = paginator.page(1)
        except EmptyPage:
            papers_page = paginator.page(paginator.num_pages)

        all_topics_db = Topic.objects.all()
        topic_dict = {
            t.topic_id: {"id": t.topic_id, "name": t.name, "keywords": t.keywords} 
            for t in all_topics_db
        }

        results = []
        for paper in papers_page:
            topics_data = []
            
            if hasattr(paper, 'topic_info') and paper.topic_info:
                multi_labels = paper.topic_info.predicted_multi_labels or []
                for label in multi_labels:
                    try:
                        topic_id_str = label.split(':')[0].replace('Topic ', '').strip()
                        topic_id = int(topic_id_str)
                        if topic_id in topic_dict:
                            topics_data.append(topic_dict[topic_id])
                    except (IndexError, ValueError):
                        continue

            results.append({
                "id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "topics": topics_data,
                "authors": [author.name for author in paper.authors.all()],
                "citation_count": paper.citation_count,
                "doi": paper.doi
            })
            
        return {
            "data": results,
            "pagination": {
                "current_page": papers_page.number,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "page_size": page_size,
                "has_next": papers_page.has_next(),
                "has_previous": papers_page.has_previous()
            }
        }
    
    @staticmethod
    def get_paper_detail(paper_id):
        try:
            paper = Paper.objects.select_related('topic_info').prefetch_related('authors').get(id=paper_id)
        except Paper.DoesNotExist:
            return None

        all_topics_db = Topic.objects.all()
        topic_dict = {
            t.topic_id: {"id": t.topic_id, "name": t.name, "keywords": t.keywords} 
            for t in all_topics_db
        }

        topics_data = []
        distribution_chart_data = []
        
        if hasattr(paper, 'topic_info') and paper.topic_info:
            multi_labels = paper.topic_info.predicted_multi_labels or []
            for label in multi_labels:
                try:
                    topic_id_str = label.split(':')[0].replace('Topic ', '').strip()
                    topic_id = int(topic_id_str)
                    if topic_id in topic_dict:
                        topics_data.append(topic_dict[topic_id])
                except (IndexError, ValueError):
                    continue

            raw_dist = paper.topic_info.topic_distribution
            
            if raw_dist and isinstance(raw_dist, list) and len(raw_dist) > 0 and isinstance(raw_dist[0], (float, int)):
                dist_with_id = [(i, prob) for i, prob in enumerate(raw_dist) if prob > 0.01]
                dist_with_id.sort(key=lambda x: x[1], reverse=True)
                
                for t_id, prob in dist_with_id[:6]:
                    if t_id in topic_dict:
                        distribution_chart_data.append({
                            "subject": topic_dict[t_id]["name"],
                            "probability": round(prob, 4),
                            "keywords": topic_dict[t_id]["keywords"] 
                        })

        authors_data = [
            {
                "id": a.id, 
                "name": a.name,
                "institution": a.institution
            } 
            for a in paper.authors.all()
        ]

        return {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "year": paper.year,
            "venue": paper.venue,
            "citation_count": paper.citation_count,
            "doi": paper.doi,
            "url": paper.url,
            "topics": topics_data,
            "authors": authors_data,
            "distribution_chart": distribution_chart_data
        }