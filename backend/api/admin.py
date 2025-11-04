from django.contrib import admin
from .models import Paper, TopicEmbedding, ClassifiedTopic, ClassifiedSubTopic

admin.site.register(Paper)
admin.site.register(TopicEmbedding)
admin.site.register(ClassifiedTopic)
admin.site.register(ClassifiedSubTopic)