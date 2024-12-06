import pytest
import threading
import requests
from slurm_job_tracker.server import ThreadedHTTPServer, CommandHandler
from slurm_job_tracker.tracker import SlurmJobTracker
from slurm_job_tracker.config import SERVER_HOST, SERVER_PORT
import os

@pytest.fixture
def tracker():
    """Fixture to initialize a SlurmJobTracker instance."""
    return SlurmJobTracker()


@pytest.fixture
def server(tracker):
    """Start the server in a separate thread."""
    server_address = (SERVER_HOST, SERVER_PORT)
    httpd = ThreadedHTTPServer(server_address, CommandHandler, tracker)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()

def test_server_submit_task(server):
    """Test the server's task submission API."""
    url = f"http://127.0.0.1:8000"
    command = {
        "command": "submit_task",
        "args": {
            "working_dir": "/test/workdir",
            "script_name": "submit_test.sh",
        },
    }
    # Use the token from the environment
    token = os.getenv("SLURM_TRACKER_TOKEN")
    assert token is not None, "SLURM_TRACKER_TOKEN not found in environment"
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, json=command, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "Task added to queue"}
