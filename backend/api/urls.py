from django.urls import path
from .views import DashboardStatsView, NetworkGraphView, ClusterListView

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('graph/', NetworkGraphView.as_view(), name='network-graph'),
    path('clusters/', ClusterListView.as_view(), name='cluster-list'),
]