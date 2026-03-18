from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Paper, Author
from .serializers import PaperListSerializer, PaperDetailSerializer, AuthorSerializer
from collections import defaultdict
from rest_framework.decorators import api_view, permission_classes # เพิ่ม permission_classes
from rest_framework.permissions import AllowAny # เพิ่ม AllowAny

# API for Paper (Search & Detail) ---
class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API สำหรับดึงข้อมูล Paper
    - List: ใช้ PaperListSerializer (ข้อมูลเบา)
    - Retrieve (ดูรายตัว): ใช้ PaperDetailSerializer (ข้อมูลเต็ม)
    """
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaperDetailSerializer
        return PaperListSerializer

    def get_queryset(self):
        # ใช้ prefetch_related เพื่อลดจำนวน Query ลง Database (เพิ่มความเร็ว)
        queryset = Paper.objects.all().prefetch_related('authors')
        
        # รับค่าจากช่อง Search Bar และ Filter ฝั่ง Frontend
        q = self.request.query_params.get('q', None)
        year = self.request.query_params.get('year', None)
        domain = self.request.query_params.get('domain', None)
        cluster_id = self.request.query_params.get('cluster_id', None)

        if q:
            # ค้นหาคำใน Title หรือ Abstract
            queryset = queryset.filter(Q(title__icontains=q) | Q(abstract__icontains=q))
        if year:
            queryset = queryset.filter(year=year)
        if domain:
            # ค้นหาเปเปอร์ที่มี Domain นี้อยู่ใน predicted_multi_labels
            queryset = queryset.filter(predicted_multi_labels__contains=domain)
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
            
        # เรียงลำดับตามปีล่าสุด หรือ ยอด Citation สูงสุด
        return queryset.order_by('-year', '-citation_count')


# --- 2. API สำหรับ Author Profile ---
class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API สำหรับดึงข้อมูล Author
    """
    queryset = Author.objects.all().prefetch_related('papers')
    serializer_class = AuthorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q', None)
        if q:
            queryset = queryset.filter(name__icontains=q)
        # เรียงตามจำนวนเปเปอร์ (ถ้ามี Field เก็บไว้) หรือดึงตัวหลักๆ ขึ้นมาก่อน
        return queryset


# --- 3. API สำหรับ Analytics & Dashboard ---

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    """Send the overall statistics to be displayed in a card at the top of the Dashboard."""
    total_papers = Paper.objects.count()
    total_authors = Author.objects.count()
    # นับจำนวน Topic Cluster ที่หาเจอ (ไม่รวมค่าว่าง)
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
    """API สำหรับดึงรายชื่อ Topic/Domain ทั้งหมดที่ไม่ซ้ำกัน นำไปทำ Dropdown Filter"""
    # ดึง cluster_label ที่ไม่เป็นค่าว่าง และเอาเฉพาะค่าที่ไม่ซ้ำกัน (distinct)
    topics = Paper.objects.exclude(cluster_label__isnull=True).values_list('cluster_label', flat=True).distinct()
    
    # กรองเอาเฉพาะชื่อที่ไม่ใช่ "Outlier / Noise" (ถ้าไม่อยากให้คนค้นหา Outlier)
    topic_list = [t for t in topics if t != "Outlier / Noise"]
    
    # เรียงตามตัวอักษรให้สวยงาม
    return Response(sorted(topic_list))

@api_view(['GET'])
@permission_classes([AllowAny])
def author_network(request):
    """
    Create Node and Link data to plot a collaboration network graph.
    Limit to the top 100 most recent papers to avoid making the graph cluttered and heavy.
    """
    limit = int(request.query_params.get('limit', 100))
    papers = Paper.objects.prefetch_related('authors').order_by('-year')[:limit]
    
    nodes_dict = {}
    links_dict = defaultdict(int)
    
    for paper in papers:
        authors = list(paper.authors.all())
        # สร้าง Nodes
        for author in authors:
            if author.id not in nodes_dict:
                nodes_dict[author.id] = {
                    "id": str(author.id),
                    "name": author.name,
                    "val": 1 # ขนาดของ Node (จะบวกเพิ่มถ้าเจอซ้ำ)
                }
            else:
                nodes_dict[author.id]["val"] += 1
                
        # สร้าง Links (จับคู่ผู้แต่งทุกคนในเปเปอร์เดียวกัน)
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                # เรียง ID เพื่อไม่ให้เกิด Link ซ้ำไปกลับ (A->B กับ B->A)
                a1, a2 = sorted([authors[i].id, authors[j].id])
                link_key = f"{a1}-{a2}"
                links_dict[link_key] += 1
                
    nodes = list(nodes_dict.values())
    links = [{"source": str(k.split('-')[0]), "target": str(k.split('-')[1]), "weight": v} for k, v in links_dict.items()]
    
    return Response({
        "nodes": nodes,
        "links": links
    })