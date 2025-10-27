from django.db import models

class Paper(models.Model):
    title = models.TextField()
    authors = models.TextField()
    year = models.IntegerField(null=True, blank=True)
    doi = models.CharField(max_length=255, unique=True)
    venue = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    fields_of_study = models.TextField(null=True, blank=True)
    citation_count = models.IntegerField(default=0)
    url = models.URLField(null=True, blank=True)
    
    # When print pr see it in Django admin
    def __str__(self):
        return f"({self.id}) {self.title} ({self.year})"
    
class SkillEmbedding(models.Model):
    skill_name = models.CharField(max_length=255, unique=True)
    embedding = models.BinaryField()  # เก็บ np array เป็น bytes
    source = models.CharField(max_length=100, default="ESCO")
    model_name = models.CharField(max_length=100, default="allenai/specter2_base")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.skill_name[:40]}..."

class ExtractedSkill(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='extracted_skills')
    author_name = models.CharField(max_length=255, null=True, blank=True)
    skill_name = models.CharField(max_length=255)
    skill_uri = models.URLField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)  #similarity between abstract and skill
    embedding_model = models.CharField(max_length=255, default="allenai/specter2_base")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.skill_name} ({self.confidence:.2f}) - {self.author_name or 'Unknown'} [{self.paper.title}]"
    
class TopicEmbedding(models.Model):
    topic_name = models.CharField(max_length=255, unique=True)
    embedding = models.BinaryField()
    source = models.CharField(max_length=100, default="MANUAL") # แหล่งที่มาของ Topic เช่น MANUAL, ACM, etc.
    model_name = models.CharField(max_length=100, default="allenai/specter2_base")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.topic_name} ({self.source})"
    
class ClassifiedTopic(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='classified_topics')
    topic_name = models.CharField(max_length=255)
    confidence = models.FloatField(default=0.0)
    embedding_model = models.CharField(max_length=255, default="allenai/specter2_base")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ป้องกันการบันทึก topic เดียวกันซ้ำสำหรับ paper และ model เดียวกัน
        unique_together = ('paper', 'topic_name', 'embedding_model')

    def __str__(self):
        return f"{self.topic_name} ({self.confidence:.2f}) - [{self.paper.title}]"
