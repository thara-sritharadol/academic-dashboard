from rest_framework import serializers
from .models import Paper, Author

# Author Serializers
class AuthorSerializer(serializers.ModelSerializer):
    works_count = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            'id', 'name', 'works_count', 'institution', 'faculty', 
            'department', 'primary_cluster', 'topic_profile'
        ]

    def get_works_count(self, obj):
        return obj.papers.count()


# Paper Serializers
class PaperListSerializer(serializers.ModelSerializer):
    authors_list = serializers.StringRelatedField(source='authors', many=True, read_only=True)

    class Meta:
        model = Paper
        fields = [
            'id', 'title', 'year', 'cluster_id', 'cluster_label', 
            'predicted_multi_labels', 'authors_list', 'citation_count'
        ]

class PaperDetailSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)

    class Meta:
        model = Paper
        fields = [
            'id', 'title', 'abstract', 'year', 'doi', 'venue', 'url',
            'cluster_id', 'cluster_label', 'predicted_multi_labels',
            'topic_distribution', 'entropy', 'authors', 'citation_count'
        ]