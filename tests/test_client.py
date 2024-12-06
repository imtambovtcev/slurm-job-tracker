import pytest
from unittest.mock import patch
from slurm_job_tracker.client import SlurmJobTrackerClient


@patch("slurm_job_tracker.client.requests.post")
def test_submit_task(mock_post):
    """Test submitting a task to the server."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "Task added to queue"}

    client = SlurmJobTrackerClient(server_host="127.0.0.1", server_port=8000, secret_token="test_token")
    response = client.submit_task("/test", "script.sh")

    assert response == {"status": "Task added to queue"}
    mock_post.assert_called_once_with(
        "http://127.0.0.1:8000",
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test_token'
        },
        data='{"command": "submit_task", "args": {"working_dir": "/test", "script_name": "script.sh"}}'
    )



@patch("slurm_job_tracker.client.requests.post")
def test_get_status(mock_post):
    """Test getting the status of running jobs."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"running_jobs": ["job1", "job2"]}

    client = SlurmJobTrackerClient(server_host="127.0.0.1", server_port=8000, secret_token="test_token")
    response = client.get_status()

    assert response == {"running_jobs": ["job1", "job2"]}
    mock_post.assert_called_once_with(
        "http://127.0.0.1:8000",
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test_token'
        },
        data='{"command": "get_status"}'
    )

@patch("slurm_job_tracker.client.requests.post")
def test_get_queue(mock_post):
    """Test getting the list of queued tasks."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "status": "Queue retrieved",
        "queued_tasks": [
            {"working_dir": "/test1", "script_name": "script1.sh"},
            {"working_dir": "/test2", "script_name": "script2.sh"}
        ]
    }

    client = SlurmJobTrackerClient(server_host="127.0.0.1", server_port=8000, secret_token="test_token")
    response = client.get_queue()

    assert response == {
        "status": "Queue retrieved",
        "queued_tasks": [
            {"working_dir": "/test1", "script_name": "script1.sh"},
            {"working_dir": "/test2", "script_name": "script2.sh"}
        ]
    }
    mock_post.assert_called_once_with(
        "http://127.0.0.1:8000",
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test_token'
        },
        data='{"command": "get_queue"}'
    )
