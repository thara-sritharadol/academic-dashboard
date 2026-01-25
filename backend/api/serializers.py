from rest_framework import serializers
from .models import Paper, Author

class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ['id', 'title', 'year', 'cluster_id', 'cluster_label']

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'works_count', 'institution']