from django.contrib import admin
from .models import Paper, Author,SkillEmbedding, ExtractedSkill, ExtractedSubSkill

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'department', 'primary_cluster')
    search_fields = ('name',)

@admin.register(Paper)
class paperAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors_text', 'year')
    search_fields = ('authors_text',)
#admin.site.register(Paper)
#admin.site.register(Author)
#admin.site.register(SkillEmbedding)
#admin.site.register(ExtractedSkill)
#admin.site.register(ExtractedSubSkill)
