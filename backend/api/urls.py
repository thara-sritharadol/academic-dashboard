from django.urls import path
from . import views

urlpatterns = [
    path('papers/', views.get_papers, name='paper-card'),
    path('papers/<int:paper_id>/', views.get_paper_detail_view, name='paper-detail'),

    path('authors/<int:author_id>/', views.get_author_detail_view, name='author-detail'),

    path('analytics/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('analytics/domain-trends/', views.domain_trends, name='domain-trends'),
    path('analytics/topics/', views.get_all_topics, name='all-topics'),
    path('analytics/top-authors/', views.top_authors),

    path('network/authors/', views.author_network, name='author-network'),
    
    path('health/', views.simple_health_check, name='health-check'),
]