from django.contrib import admin
from .models import Paper, ExtractedSkill, SkillEmbedding, TopicEmbedding, ClassifiedTopic

admin.site.register(Paper)
admin.site.register(ExtractedSkill)
admin.site.register(SkillEmbedding)
admin.site.register(TopicEmbedding)
admin.site.register(ClassifiedTopic)