#api/management/commands/cluster_papers.py
#Not Use
from django.core.management.base import BaseCommand
from api.services.clustering import ClusteringService 

class Command(BaseCommand):
    help = 'Groups papers into clusters using K-Means algorithm'

    def add_arguments(self, parser):
        #parameter --k for Define a group number command line
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