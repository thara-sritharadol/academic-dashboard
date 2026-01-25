# api/management/commands/cluster_papers.py
from django.core.management.base import BaseCommand
# Import Service จากโฟลเดอร์ services
from api.services.clustering import ClusteringService 

class Command(BaseCommand):
    help = 'Groups papers into clusters using K-Means algorithm'

    def add_arguments(self, parser):
        # เพิ่ม parameter --k เพื่อกำหนดจำนวนกลุ่มได้จาก command line
        parser.add_argument(
            '--k',
            type=int,
            default=5,
            help='Number of clusters to create (default: 5)'
        )

    def handle(self, *args, **options):
        n_clusters = options['k']
        
        # เรียกใช้ Service
        service = ClusteringService(n_clusters=n_clusters)
        service.run()