import pytest
from unittest.mock import patch
from slurm_job_tracker.client import send_command


@patch("slurm_job_tracker.client.requests.post")
def test_send_command(mock_post):
    """Test sending a command to the server."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "Task submitted"}

    command = {"command": "submit_task", "args": {"working_dir": "/test", "script_name": "script.sh"}}
    response = send_command(command)

    assert response == {"status": "Task submitted"}
    mock_post.assert_called_once()
