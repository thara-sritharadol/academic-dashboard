import pytest
from django.core.management import call_command
from api.models import Author, Paper

#Use Fake DB
@pytest.mark.django_db
def test_batch_fetch_papers_success(mocker):

    author = Author.objects.create(
        name="John Doe", 
        faculty="Engineering",
        openalex_id=None
    )

    mock_stream = mocker.patch('api.management.commands.batch_fetch_papers.stream_papers_from_apis')
    
    def fake_stream(*args, **kwargs):
        yield 1  # the number of papers published (total_results).
        yield {  # the paper data.
            "doi": "10.999/test-doi",
            "title": "AI in Thammasat",
            "year": 2026,
            "venue": "TU Journal",
            "authors_struct": [
                {"name": "John Doe", "openalex_id": "A123456"}
            ]
        }
    
    # Replace the real function with a simulated one.
    mock_stream.side_effect = fake_stream

    call_command('batch_fetch_papers', batch_size=1)

    # Verify the results in the Fake database.
    assert Paper.objects.count() == 1
    
    saved_paper = Paper.objects.first()
    assert saved_paper.title == "AI in Thammasat"
    assert saved_paper.doi == "10.999/test-doi"

    # Check if the many-to-many relationships are correctly linked.
    assert author in saved_paper.authors.all()

    # Check if the instructor's openalex_id has been updated.
    updated_author = Author.objects.get(id=author.id)
    assert updated_author.openalex_id == "A123456"