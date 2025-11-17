from django.contrib import admin
from .models import Paper, SkillEmbedding, ExtractedSkill, ExtractedSubSkill

admin.site.register(Paper)
admin.site.register(SkillEmbedding)
admin.site.register(ExtractedSkill)
admin.site.register(ExtractedSubSkill)