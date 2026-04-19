import pytest
from io import StringIO
from django.core.management import call_command
from api.models import Author, Paper
from backend.api.pipelines.author_profile_service import AuthorProfileService

@pytest.mark.django_db
def test_generate_all_profiles_logic():

    author = Author.objects.create(name="Prof. Data")
    
    Paper.objects.create(
        doi="10.1/p1", title="P1", cluster_id=2, topic_distribution=[0.1, 0.9]
    )

    Paper.objects.create(
        doi="10.1/p2", title="P2", cluster_id=2, topic_distribution=[0.3, 0.7]
    )

    Paper.objects.create(
        doi="10.1/p3", title="P3", cluster_id=-1, topic_distribution=[0.5, 0.5]
    )
    
    author.papers.add(Paper.objects.get(title="P1"))
    author.papers.add(Paper.objects.get(title="P2"))
    author.papers.add(Paper.objects.get(title="P3"))

    # Service
    result = AuthorProfileService.generate_all_profiles()

    # Check Results
    assert result["updated"] == 1
    
    # Update to DB
    author.refresh_from_db()

    # Check the Primary Cluster: It has 2, 2, -1 -> We should discard -1 and choose 2 as the primary cluster.
    assert author.primary_cluster == "2"

    # Check Topic Profile: Must be the average of [0.1, 0.9], [0.3, 0.7], [0.5, 0.5]
    # (0.1+0.3+0.5)/3 = 0.3
    # (0.9+0.7+0.5)/3 = 0.7
    expected_profile = [0.3, 0.7]
    
    # Use pytest.approx to prevent errors from decimal places in Float values.
    assert author.topic_profile == pytest.approx(expected_profile)

def test_generate_author_profiles_command(mocker):
    # Command
    mock_service = mocker.patch('api.management.commands.generate_author_profiles.AuthorProfileService')
    mock_service.generate_all_profiles.return_value = {
        "status": "success", 
        "updated": 5,
        "message": "Successfully generated profiles for 5 authors."
    }

    out = StringIO()
    call_command('generate_author_profiles', stdout=out)
    
    output_text = out.getvalue()
    assert "Done! Successfully generated profiles for 5 authors." in output_text