import pytest
from api.services.tu_sync_service import TUSyncService

@pytest.fixture
def service():
    return TUSyncService(api_key="fake_api_key")

def test_fetch_faculties_success(mocker, service):
    # 1. Mock requests.get
    mock_get = mocker.patch('requests.get')
    
    # 2. Mock Response for APIs
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "status": True,
        "data": [{"faculty_en": "Engineering"}, {"faculty_en": "Science"}]
    }

    # 3. call fucntion
    result = service.fetch_faculties()

    # 4. Assert
    assert len(result) == 2
    assert result[0]["faculty_en"] == "Engineering"
    mock_get.assert_called_once() # Verify that requests.get was actually executed at once.

def test_fetch_faculties_api_error(mocker, service):
    # Simulate API outages or exceptions.
    mock_get = mocker.patch('requests.get', side_effect=Exception("API is down"))
    
    result = service.fetch_faculties()
    
    assert result == []


def test_sync_authors_success(mocker, service):
    mocker.patch.object(service, 'fetch_faculties', return_value=[{"faculty_en": "Engineering"}])
    
    mock_instructors = [
        {
            "First_Name_En": "John", 
            "Last_Name_En": "Doe", 
            "Email": "john@tu.ac.th", 
            "Faculty_Name_En": "Engineering"
        }
    ]
    mocker.patch.object(service, 'fetch_instructors', return_value=mock_instructors)

    # Simulating a Django database to avoid saving to a real database.
    # Return (author_obj, created) = (Mock, True)
    mock_db = mocker.patch('api.models.Author.objects.update_or_create', return_value=(mocker.Mock(), True))

    mocker.patch('time.sleep')

    result = service.sync_authors()

    # Logic
    assert result["status"] == "success"
    assert result["saved"] == 1
    assert result["updated"] == 0

    # Check if it's attempting to save to the database with the correct filename. (John Doe)
    mock_db.assert_called_once_with(
        name="John Doe",
        defaults={
            "institution": "Thammasat University",
            "faculty": "Engineering",
            "email": "john@tu.ac.th"
        }
    )