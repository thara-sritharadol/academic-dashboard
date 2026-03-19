from django.contrib import admin
from .models import Paper, Author

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'department', 'primary_cluster')
    search_fields = ('name', 'faculty')

@admin.register(Paper)
class paperAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors_text', 'year')
    search_fields = ('authors_text', 'id', 'cluster_label', 'openalex_concepts')