from django.db import models

"""
class Author(models.Model):
    openalex_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)

    faculty = models.CharField(max_length=255, null=True, blank=True)
    institution = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    last_fetched_papers = models.DateTimeField(null=True, blank=True)

    primary_cluster = models.IntegerField(null=True, blank=True)
    topic_profile = models.JSONField(null=True, blank=True)
    faculty = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name
"""

"""
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
"""

class Author(models.Model):
    openalex_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    institution = models.CharField(max_length=255, null=True, blank=True, default="Thammasat University")
    faculty = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Paper(models.Model):
    doi = models.CharField(max_length=255, unique=True)
    title = models.TextField()
    year = models.IntegerField(null=True, blank=True, db_index=True)
    venue = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    citation_count = models.IntegerField(default=0)
    url = models.URLField(null=True, blank=True)

    # Many-to-Many
    authors = models.ManyToManyField(Author, related_name="papers")

    def __str__(self):
        return f"({self.year}) {self.title[:50]}..."

# ML Section
class Topic(models.Model):
    #cluster_id from BERTopic (-1, 0, 1, 2...)
    topic_id = models.IntegerField(unique=True, db_index=True) 
    
    # name from LLM (like "Clinical Stroke Management")
    name = models.CharField(max_length=255) 
    
    # Keyword's Array
    keywords = models.JSONField(help_text="Keywords from BERTopic")

    def __str__(self):
        return f"Topic {self.topic_id}: {self.name}"

class PaperTopicInteraction(models.Model):
    paper = models.OneToOneField(Paper, on_delete=models.CASCADE, related_name="topic_info")
    primary_topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="primary_papers")
    
    # Multi-label
    related_topics = models.ManyToManyField(Topic, related_name="related_papers", blank=True)
    
    # Prob Array
    topic_distribution = models.JSONField(null=True, blank=True)
    entropy = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"ML Info for {self.paper.doi}"
    
class FacultyTopicStat(models.Model):
    faculty = models.CharField(max_length=255)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    total_papers = models.IntegerField(default=0)
    total_citations = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('faculty', 'topic')

    def __str__(self):
        return f"{self.faculty} - {self.topic.name} ({self.total_papers} papers)"
    
class YearlyTopicStat(models.Model):
    year = models.IntegerField(db_index=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="yearly_stats")
    total_papers = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('year', 'topic')

    def __str__(self):
        return f"{self.year} - {self.topic.name}: {self.total_papers}"
    
class CoAuthorship(models.Model):
    # Link
    author_a = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="connections_as_a")
    author_b = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="connections_as_b")
    
    weight = models.IntegerField(default=1)
    
    # Domain
    shared_topics = models.ManyToManyField(Topic, blank=True)

    class Meta:
        unique_together = ('author_a', 'author_b')

    def __str__(self):
        return f"{self.author_a.name} <-> {self.author_b.name} (Weight: {self.weight})"