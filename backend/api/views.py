from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q

from api.services.analytics_service import AnalyticsService
from api.services.authors_services import AuthorsService
from api.services.papers_services import PapersService

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
    try:
        limit = int(request.query_params.get('limit', 200))
    except ValueError:
        limit = 200

    domains_param = request.query_params.get('domains') or request.query_params.get('domain', None)
    data = AuthorsService.get_author_network(limit=limit, domains_param=domains_param)
    
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def top_authors(request):
    data = AuthorsService.get_top_author()
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_papers(request):
    page_num = int(request.GET.get('page', 1))
    size = int(request.GET.get('page_size', 12))
    domains = request.GET.get('domains', None)
    search_text = request.GET.get('search', None) 
    author_id_param = request.GET.get('author_id', None)
    
    data = PapersService.get_paper_cards(
        page=page_num, 
        page_size=size, 
        domains_param=domains,
        search_query=search_text,
        author_id=author_id_param
    )
    
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_paper_detail_view(request, paper_id):
    result = PapersService.get_paper_detail(paper_id)
    
    if result is None:
        return Response({"error": "Paper not found"}, status=404)
        
    return Response(result)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_author_detail_view(request, author_id):
    result = AuthorsService.get_author_detail(author_id)

    if result is None:
        return Response({"error": "Researcher not found"}, status=404)
    
    return Response(result)

@api_view(['GET'])
@permission_classes([AllowAny])
def simple_health_check(request):
    return Response({"status": "ok"}, status=200)