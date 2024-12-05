import pytest
import threading
import requests
from slurm_job_tracker.server import ThreadedHTTPServer, CommandHandler
from slurm_job_tracker.tracker import SlurmJobTracker
from slurm_job_tracker.config import SERVER_HOST, SERVER_PORT


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
    url = f"http://{SERVER_HOST}:{SERVER_PORT}"
    command = {
        "command": "submit_task",
        "args": {
            "working_dir": "/test/workdir",
            "script_name": "submit_test.sh",
        },
    }
    response = requests.post(url, json=command)
    assert response.status_code == 200
    assert response.json() == {"status": "Task submitted"}
