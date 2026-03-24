from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Use DefaultRouter to automatically create GET, POST, and PUT routes for ViewSets.
router = DefaultRouter()
router.register(r'papers', views.PaperViewSet, basename='paper')
router.register(r'authors', views.AuthorViewSet, basename='author')

urlpatterns = [
    # 1. API for data retrieval (enabled via router)
    # Ex. /api/papers/, /api/papers/123/, /api/authors/
    path('', include(router.urls)),
    
    # 2. API กลุ่ม Analytics & Dashboard
    # Ex. /api/analytics/summary/
    path('analytics/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('analytics/domain-trends/', views.domain_trends, name='domain-trends'),
    path('analytics/topics/', views.get_all_topics, name='all-topics'),
    path('analytics/top-authors/', views.top_authors),
    path('network/authors/', views.author_network, name='author-network'),
]