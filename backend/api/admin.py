from django.contrib import admin
from .models import Paper, ExtractedSkill, SkillEmbedding

admin.site.register(Paper)
admin.site.register(ExtractedSkill)
admin.site.register(SkillEmbedding)