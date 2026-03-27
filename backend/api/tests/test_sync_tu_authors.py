import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError

COMMAND_NAME = 'sync_tu_authors'

#Test CI

def test_command_success(mocker):

    mock_service_class = mocker.patch('api.management.commands.sync_tu_authors.TUSyncService')
    
    # Simulate an instance of a service and return the resulting value.
    mock_instance = mock_service_class.return_value
    mock_instance.sync_authors.return_value = {
        "status": "success",
        "saved": 15,
        "updated": 5
    }

    # Create a dummy screen to capture what the Command is typing (self.stdout.write).
    out = StringIO()

    # Run the command as you would by typing `python manage.py sync_tu_authors --api_key="fake" --faculty="Science"`.
    call_command(COMMAND_NAME, api_key='fake_token', faculty='Science', stdout=out)

    # Check if the command creates the service with the correct api_key.
    mock_service_class.assert_called_once_with(api_key='fake_token')
    
    # Check if the command calls the sync_authors method with the correct faculty.
    mock_instance.sync_authors.assert_called_once_with(specific_faculty='Science')

    # Check the messages sent through the terminal.
    output_text = out.getvalue()
    assert "Sync Complete!" in output_text
    assert "New Authors Added: 15" in output_text
    assert "Existing Authors Updated: 5" in output_text

def test_command_missing_required_args():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME, faculty='Science')