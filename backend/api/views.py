from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from django.db.models import Count, Q
from .models import Paper, Author
from .serializers import AuthorSerializer
from rest_framework import permissions
from collections import defaultdict, Counter

class DashboardStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total_authors = Author.objects.count()
        total_papers = Paper.objects.count()
        #นับจำนวน paper ในแต่ละ cluster
        analyzed_papers = Paper.objects.filter(abstract__isnull=False).exclude(abstract='').count()

        clusters = Paper.objects.values('cluster_label') \
            .exclude(cluster_label__isnull=True) \
            .annotate(count=Count('id')) \
            .order_by('-count')
        
        return Response({
            "total_authors": total_authors,
            "total_papers": total_papers,
            "analyzed_papers": analyzed_papers,
            "cluster_stats": clusters
        })

class NetworkGraphView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # 1. ลอง Top 500 Authors
        authors = Author.objects.annotate(works_count=Count('papers')).order_by('-works_count')[:500]
        #แปลงเป็น Set ให้หาเร็วขึ้น
        author_ids = set([a.id for a in authors]) 

        # 2. สร้าง Nodes
        nodes = []
        for author in authors:
            nodes.append({
                "id": author.id,
                "name": author.name,
                "val": author.works_count,
                "group": author.primary_cluster or "Uncategorized",
                "faculty": author.faculty or "",
                "dept": author.department or ""
            })

        # 3. ดึง Papers
        #filter เอาเฉพาะ Paper ที่ Top 500 คนนี้เขียน
        #distinct ป้องกัน Paper ซ้ำ
        #prefetch_related ดึงข้อมูล authors มารอไว้เลย
        papers = Paper.objects.filter(authors__id__in=author_ids)\
                              .distinct()\
                              .prefetch_related('authors')
        
        # 4. สร้าง Links
        links = []
        for paper in papers:
            #ดึง authors จาก cache
            #เลือกคนที่เป็น Top 500 (author_ids)
            co_authors = [a.id for a in paper.authors.all() if a.id in author_ids]
            
            count = len(co_authors)
            
            #ต้องมีผู้เขียนร่วมมากกว่า 1 คนถึงจะมีเส้นเชื่อม
            if count > 1:
                for i in range(count):
                    for j in range(i + 1, count):
                        links.append({
                            "source": co_authors[i],
                            "target": co_authors[j],
                            "paper_id": paper.id
                        })

        return Response({
            "nodes": nodes,
            "links": links
        })

class ClusterListView(APIView):
    def get(self, request):
        #ดึงรายชื่อกลุ่ม
        #[{"cluster_id": 0, "label": "network, 5g"}, ...]
        data = Paper.objects.values('cluster_id', 'cluster_label').distinct().order_by('cluster_id')
        return Response(data)