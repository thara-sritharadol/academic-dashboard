from django.db import models

class Author(models.Model):
    openalex_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    institution = models.CharField(max_length=255, null=True, blank=True)
    primary_cluster = models.CharField(max_length=255, null=True, blank=True)

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

    cluster_id = models.IntegerField(null=True, blank=True, db_index=True) # เก็บเลขกลุ่ม เช่น 0, 1, 2
    cluster_label = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"({self.id}) {self.title}"
    
class SkillEmbedding(models.Model):
    skill_name = models.CharField(max_length=255) 
    embedding = models.BinaryField()
    source = models.CharField(max_length=100, default="MANUAL")
    model_name = models.CharField(max_length=100, default="all-mpnet-base-v2")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('skill_name', 'source', 'model_name')

    def __str__(self):
        return f"[{self.source}] {self.skill_name} ({self.model_name})"
    
class ExtractedSkill(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='classified_skills')
    skill_name = models.CharField(max_length=255)
    vote_count = models.IntegerField(default=0) 
    level = models.IntegerField(null=True, blank=True)
    level_0_skill = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        db_index=True
    )
    embedding_model = models.CharField(max_length=255, default="all-mpnet-base-v2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('paper', 'skill_name', 'embedding_model')

    def __str__(self):
        l0_str = f" (L0: {self.level_0_skill})" if self.level_0_skill else ""
        return f"[L{self.level or '?'}] {self.skill_name}{l0_str} ({self.vote_count} votes) ({self.paper.authors})"
    
class ExtractedSubSkill(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='classified_sub_skillss')
    skill_name = models.CharField(max_length=255)
    confidence = models.FloatField(default=0.0)
    source_sentence = models.TextField(null=True, blank=True) 
    embedding_model = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.skill_name} ({self.confidence:.2f}) ({self.paper.title})"
