from django.db import models

class Author(models.Model):
    openalex_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)

    faculty = models.CharField(max_length=255, null=True, blank=True)
    institution = models.CharField(max_length=255, default="Thammasat University")
    email = models.EmailField(null=True, blank=True)

    last_fetched_papers = models.DateTimeField(null=True, blank=True)

    primary_cluster = models.CharField(max_length=255, null=True, blank=True)
    topic_profile = models.JSONField(null=True, blank=True)
    faculty = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Paper(models.Model):
    title = models.TextField()
    authors_text = models.TextField(null=True, blank=True) 
    authors = models.ManyToManyField(Author, related_name="papers")
    
    year = models.IntegerField(null=True, blank=True)
    doi = models.CharField(max_length=255, unique=True)
    venue = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    fields_of_study = models.TextField(null=True, blank=True)
    citation_count = models.IntegerField(default=0)
    url = models.URLField(null=True, blank=True)

    openalex_concepts = models.JSONField(null=True, blank=True, help_text="List of concepts from OpenAlex")

    cluster_id = models.IntegerField(null=True, blank=True, db_index=True)
    cluster_label = models.CharField(max_length=255, null=True, blank=True)
    
    predicted_multi_labels = models.JSONField(null=True, blank=True, help_text="List of predicted labels")

    topic_keywords = models.JSONField(null=True, blank=True, help_text="Raw keywords from BERTopic")
    
    topic_distribution = models.JSONField(null=True, blank=True)
    entropy = models.FloatField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"({self.id}) {self.title}"