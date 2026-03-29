import sys
from unittest.mock import MagicMock

heavy_modules = [
    'bertopic', 'umap', 'spacy', 'sklearn', 'sklearn.feature_extraction.text',
    'gensim', 'gensim.models.coherencemodel', 'gensim.corpora.dictionary',
    'plotly.express', 'matplotlib.pyplot', 'seaborn', 'pandas'
]

for mod in heavy_modules:
    sys.modules[mod] = MagicMock()


import pytest
from django.core.management import call_command
from api.models import Paper
import api.management.commands.apply_bertopic_clusters

@pytest.mark.django_db
def test_apply_bertopic_command_success(mocker):
    # Mock Paper In Test DB
    paper1 = Paper.objects.create(title="AI Model", abstract="Deep learning is great.", doi="10.123/ai-paper",)
    paper2 = Paper.objects.create(title="DevOps", abstract="CI/CD pipelines automation.", doi="10.123/devops-paper",)

    # Mock BERTopicService
    mock_bertopic_class = mocker.patch('api.management.commands.apply_bertopic_clusters.BERTopicService')
    mock_bertopic_instance = mock_bertopic_class.return_value
    
    # Mock fit_transform (topics array, probabilities array)
    mock_bertopic_instance.fit_transform.return_value = (
        [0, 1], 
        [[0.9, 0.1], [0.1, 0.9]]
    )
    
    # LLM no naming
    mock_bertopic_instance.topic_model.get_topic.return_value = [("ai", 0.5), ("model", 0.4)]

    # LLM naming
    mock_gemini_class = mocker.patch('api.management.commands.apply_bertopic_clusters.GeminiNamingService')
    mock_gemini_instance = mock_gemini_class.return_value
    
    mock_gemini_instance.generate_topic_names.return_value = {
        "0": "Artificial Intelligence",
        "1": "Software Engineering"
    }

    # Command
    call_command('apply_bertopic_clusters', auto_tune=True, gemini_key="fake-key")

    # Check the results in the database.
    paper1.refresh_from_db()
    paper2.refresh_from_db()

    # Check if the first paper is correctly grouped into Topic 0 and named according to Gemini.
    assert paper1.cluster_id == 0
    assert paper1.cluster_label == "Topic 0: Artificial Intelligence"
    assert paper1.topic_distribution == [0.9, 0.1]

    assert paper2.cluster_id == 1
    assert paper2.cluster_label == "Topic 1: Software Engineering"