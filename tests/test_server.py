import os
import socket
import threading

import pytest
import requests

from slurm_job_tracker.server import CommandHandler, ThreadedHTTPServer
from slurm_job_tracker.tracker import SlurmJobTracker


def get_free_port():
    """Get a free port for the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def tracker():
    """Fixture to initialize a SlurmJobTracker instance."""

    return SlurmJobTracker()


@pytest.fixture
def server(tracker):
    free_port = get_free_port()
    server_address = ("127.0.0.1", free_port)
    httpd = ThreadedHTTPServer(server_address, CommandHandler, tracker)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()


def test_server_submit_task(server):
    """Test the server's task submission API."""
    server_port = server.server_address[1]
    print(f"Server running on port {server_port}")
    url = f"http://127.0.0.1:{server_port}"
    command = {
        "command": "submit_task",
        "args": {
            "working_dir": "/test/workdir",
            "script_name": "submit_test.sh",
        },
    }

    test_token = os.getenv("SLURM_TRACKER_TOKEN", "")
    headers = {"Authorization": f"Bearer {test_token}"}

    response = requests.post(url, json=command, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "Task added to queue"}
