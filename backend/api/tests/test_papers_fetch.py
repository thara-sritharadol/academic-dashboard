import pytest
from api.services.papers_fetch import _reconstruct_openalex_abstract, _enrich_with_semantic_scholar, stream_papers_from_apis

def test_reconstruct_openalex_abstract():
    mock_index = {
        "AI": [0, 3],
        "is": [1],
        "cool": [2]
    }
    
    result = _reconstruct_openalex_abstract(mock_index)
    
    assert result == "AI is cool AI"

def test_reconstruct_openalex_abstract_empty():
    # Test the case where the API does not return an abstract value (None or {}).
    assert _reconstruct_openalex_abstract(None) is None
    assert _reconstruct_openalex_abstract({}) is None

def test_enrich_with_semantic_scholar_success(mocker):
    # Simulate a `requests.get` command to the path of the `papers_fetch.py` file.
    mock_get = mocker.patch('api.services.papers_fetch.requests.get')
    
    # Semantic Scholar Response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "abstract": "This is a test abstract.",
        "fieldsOfStudy": ["Computer Science", "AI"],
        "citationCount": 42
    }
    
    # Call
    result = _enrich_with_semantic_scholar("10.1234/test")
    
    # Check if the data is formatted correctly (note that fields_of_study are joined with commas).
    assert result["abstract"] == "This is a test abstract."
    assert result["fields_of_study"] == "Computer Science,AI"
    assert result["citation_count"] == 42

def test_stream_from_openalex_success(mocker):
    # Simulate making API calls to two locations: finding the instructor's ID and finding the paper.
    mocker.patch('api.services.papers_fetch._get_openalex_author_id', return_value="A1234")
    mock_get = mocker.patch('api.services.papers_fetch.requests.get')
    
    # Simulate the data that OpenAlex will send back as a response to the paper.
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "meta": {"count": 1},
        "results": [
            {
                "doi": "https://doi.org/10.999/test",
                "title": "Deep Learning for TU",
                "publication_year": 2026,
                "authorships": [
                    {"author": {"display_name": "Somsak", "id": "A1234"}}
                ]
            }
        ]
    }

    # Call the generator (currently, result_generator doesn't execute the code inside yet, it's just preparing).
    result_generator = stream_papers_from_apis(author="Somsak", source="openalex")
    
    # Use next() to retrieve the first yield value (number of papers).
    total_results = next(result_generator)
    assert total_results == 1
    
    # Use next() to retrieve the first yield value (number of papers).
    paper_data = next(result_generator)
    
    # Please check if the data has been correctly extracted. (The link https://doi.org/ must be removed.)
    assert paper_data["doi"] == "10.999/test"
    assert paper_data["title"] == "Deep Learning for TU"
    assert paper_data["year"] == 2026
    assert paper_data["authors_struct"][0]["name"] == "Somsak"