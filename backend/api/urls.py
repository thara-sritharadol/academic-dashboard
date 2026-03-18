from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ใช้ DefaultRouter สำหรับสร้างเส้นทาง GET, POST, PUT ให้อัตโนมัติสำหรับ ViewSets
router = DefaultRouter()
router.register(r'papers', views.PaperViewSet, basename='paper')
router.register(r'authors', views.AuthorViewSet, basename='author')

urlpatterns = [
    # 1. API กลุ่ม ค้นหาข้อมูล (เปิดใช้ผ่าน Router)
    # เช่น /api/papers/, /api/papers/123/, /api/authors/
    path('', include(router.urls)),
    
    # 2. API กลุ่ม Analytics & Dashboard
    # เช่น /api/analytics/summary/
    path('analytics/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('analytics/domain-trends/', views.domain_trends, name='domain-trends'),
    path('network/authors/', views.author_network, name='author-network'),
]