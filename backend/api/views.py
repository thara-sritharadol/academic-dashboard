from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Paper, Author
from .serializers import PaperListSerializer, PaperDetailSerializer, AuthorSerializer
from collections import defaultdict
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# API for Paper (Search & Detail)

class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaperDetailSerializer
        return PaperListSerializer

    def get_queryset(self):
        queryset = Paper.objects.all().prefetch_related('authors')
        
        q = self.request.query_params.get('q', None)
        year = self.request.query_params.get('year', None)
        domain = self.request.query_params.get('domain', None)
        cluster_id = self.request.query_params.get('cluster_id', None)

        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(abstract__icontains=q))
        if year:
            queryset = queryset.filter(year=year)
            
        if domain:
            # Cut a sentence and take only the first word (e.g., from "Topic 3: stroke..." to "Topic 3").
            domain_prefix = domain.split(':')[0].strip()
            
            matching_ids = []
            for paper in queryset:
                if paper.predicted_multi_labels:
                    # Loop through and check if there are any labels in the paper that "begin with" the words "Topic 3".
                    has_match = any(label.startswith(domain_prefix) for label in paper.predicted_multi_labels)
                    if has_match:
                        matching_ids.append(paper.id)
                        
            # Filter the QuerySet using the ID that matches the condition.
            queryset = queryset.filter(id__in=matching_ids)
            
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
            
        return queryset.order_by('-year', '-citation_count')


# API for Author Profile
class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for Author
    """
    queryset = Author.objects.all().prefetch_related('papers')
    serializer_class = AuthorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q', None)
        if q:
            queryset = queryset.filter(name__icontains=q)
        # Sort by the number of papers (if a field is saved) or bring up the most important ones first.
        return queryset


# API สำหรับ Analytics & Dashboard

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    """Send the overall statistics to be displayed in a card at the top of the Dashboard."""
    total_papers = Paper.objects.count()
    total_authors = Author.objects.count()
    # Count the number of Topic Clusters found (excluding empty ones).
    total_clusters = Paper.objects.exclude(cluster_label__isnull=True).values('cluster_label').distinct().count()
    
    return Response({
        'total_papers': total_papers,
        'total_authors': total_authors,
        'total_clusters': total_clusters
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def domain_trends(request):
    """Extract the number of papers broken down by year and major domain (for plotting a line chart)."""
    # Extract only papers that include a year and a Cluster Label.
    papers = Paper.objects.exclude(year__isnull=True).exclude(cluster_label__isnull=True)
    
    # Count the number (Group By Year, Cluster_Label)
    data = papers.values('year', 'cluster_label').annotate(count=Count('id')).order_by('year')
    
    # Format the chart so the frontend can easily use it with Recharts/ECharts.
    # [ {"year": 2020, "Mathematics": 15, "Computer science": 20}, ... ]
    trend_dict = defaultdict(dict)
    for item in data:
        y = item['year']
        lbl = item['cluster_label']
        trend_dict[y]['year'] = str(y)
        trend_dict[y][lbl] = item['count']
        
    result = list(trend_dict.values())
    return Response(result)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_topics(request):
    """An API for retrieving a list of all unique topics/domains to create a dropdown filter."""
    # Extract non-empty cluster_label values ​​and select only unique (distinct) values.
    topics = Paper.objects.exclude(cluster_label__isnull=True).values_list('cluster_label', flat=True).distinct()
    
    # Filter out only names that are not "Outlier / Noise" (if you don't want people to search for Outlier).
    topic_list = [t for t in topics if t != "Outlier / Noise"]
    
    # Arrange them neatly in alphabetical order.
    return Response(sorted(topic_list))

@api_view(['GET'])
@permission_classes([AllowAny])
def author_network(request):
    limit = int(request.query_params.get('limit', 200))
    # Change to accepting parameters named 'domains'.
    domains_param = request.query_params.get('domains', None) 
    
    papers_query = Paper.objects.prefetch_related('authors').order_by('-year')
    
    papers = []
    if domains_param:
        # Slice the string using commas and cut out only the words "Topic X".
        selected_prefixes = [d.split(':')[0].strip() for d in domains_param.split(',')]
        
        for p in papers_query:
            if p.predicted_multi_labels:
                # Check if this paper has any labels that match one of the topics we've selected.
                has_match = any(
                    any(label.startswith(prefix) for prefix in selected_prefixes) 
                    for label in p.predicted_multi_labels
                )
                if has_match:
                    papers.append(p)
                    if len(papers) >= limit:
                        break
    else:
        papers = papers_query[:limit]
        
    nodes_dict = {}
    links_dict = defaultdict(int)
    
    for paper in papers:
        authors = list(paper.authors.all())
        
        # Loop through the nodes and put the faculties in the same location.
        for author in authors:
            if author.id not in nodes_dict:
                nodes_dict[author.id] = {
                    "id": str(author.id),
                    "name": author.name,
                    "val": 1,
                    "group": paper.cluster_label if paper.cluster_label else "Unknown",
                    "faculty": author.faculty
                }
            else:
                nodes_dict[author.id]["val"] += 1
                
        # Links
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                a1, a2 = sorted([authors[i].id, authors[j].id])
                link_key = f"{a1}-{a2}"
                links_dict[link_key] += 1

    nodes = list(nodes_dict.values())
    links = [{"source": str(k.split('-')[0]), "target": str(k.split('-')[1]), "weight": v} for k, v in links_dict.items()]
    
    return Response({"nodes": nodes, "links": links})