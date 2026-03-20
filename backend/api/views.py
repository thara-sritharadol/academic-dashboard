from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q

from .models import Paper, Author
from .serializers import PaperListSerializer, PaperDetailSerializer, AuthorSerializer
from api.services.analytics_service import AnalyticsService  # นำเข้า Service ตัวใหม่

# ==========================================
# API for Paper (Search & Detail)
# ==========================================
class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve': return PaperDetailSerializer
        return PaperListSerializer

    def get_queryset(self):
        queryset = Paper.objects.all().prefetch_related('authors')
        
        q = self.request.query_params.get('q', None)
        year = self.request.query_params.get('year', None)
        domain = self.request.query_params.get('domain', None)
        cluster_id = self.request.query_params.get('cluster_id', None)

        if q: queryset = queryset.filter(Q(title__icontains=q) | Q(abstract__icontains=q))
        if year: queryset = queryset.filter(year=year)
        if domain:
            domain_prefix = domain.split(':')[0].strip()
            search_term = f'"{domain_prefix}:'
            queryset = queryset.filter(predicted_multi_labels__icontains=search_term)
        if cluster_id: queryset = queryset.filter(cluster_id=cluster_id)
            
        return queryset.order_by('-year', '-citation_count')


# ==========================================
# API for Author Profile
# ==========================================
class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all().prefetch_related('papers')
    serializer_class = AuthorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q', None)
        if q: queryset = queryset.filter(name__icontains=q)
        return queryset


# ==========================================
# API For Analytics & Dashboard
# ==========================================
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    data = AnalyticsService.get_dashboard_summary()
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def domain_trends(request):
    data = AnalyticsService.get_domain_trends()
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_topics(request):
    data = AnalyticsService.get_all_topics()
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def author_network(request):
    limit = int(request.query_params.get('limit', 200))
    domains_param = request.query_params.get('domains', None) 
    data = AnalyticsService.get_author_network(limit, domains_param)
    return Response(data)