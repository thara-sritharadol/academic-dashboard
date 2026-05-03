from collections import defaultdict
from api.models import Paper, Author, Topic, YearlyTopicStat

class AnalyticsService:
    TU_INSTITUTION_NAME = "Thammasat University"

    @staticmethod
    def get_dashboard_summary():
        return {
            'total_papers': Paper.objects.count(),
            'total_authors': Author.objects.filter(institution=AnalyticsService.TU_INSTITUTION_NAME).count(),
            'total_clusters': Topic.objects.exclude(topic_id=-1).count()
        }

    @staticmethod
    def get_domain_trends():
        stats = YearlyTopicStat.objects.select_related('topic').order_by('year')
        
        trend_dict = defaultdict(dict)
        for stat in stats:
            y = stat.year
            lbl = stat.topic.name
            trend_dict[y]['year'] = str(y)
            trend_dict[y][lbl] = stat.total_papers
            
        return list(trend_dict.values())

    @staticmethod
    def get_all_topics():
        topics = Topic.objects.exclude(topic_id=-1).order_by('topic_id')
        
        return [
            {
                "topic_id": t.topic_id,
                "name": t.name,
                "keywords": t.keywords,
            } for t in topics
        ]