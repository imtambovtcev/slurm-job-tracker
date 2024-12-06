import json
import logging

import requests

from .config import SECRET_TOKEN, SERVER_HOST, SERVER_PORT


class SlurmJobTrackerClient:
    """Client to communicate with the Slurm Job Tracker server."""

    def __init__(self, server_host=SERVER_HOST, server_port=SERVER_PORT, secret_token=SECRET_TOKEN):
        self.server_url = f"http://{server_host}:{server_port}"
        self.headers = {'Content-Type': 'application/json'}
        if secret_token:
            self.headers['Authorization'] = f"Bearer {secret_token}"

    def send_command(self, command):
        """Send a generic command to the server."""
        try:
            response = requests.post(self.server_url, headers=self.headers, data=json.dumps(command))
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error communicating with server: {e}")
            return None

    def submit_task(self, working_dir, script_name="submit_gpaw_alec.sh"):
        """Submit a new task to the job tracker."""
        command = {
            "command": "submit_task",
            "args": {"working_dir": working_dir, "script_name": script_name}
        }
        return self.send_command(command)

    def get_status(self):
        """Retrieve the current status of running jobs."""
        command = {"command": "get_status"}
        return self.send_command(command)

    def get_queue(self):
        """Retrieve the list of tasks in the submission queue."""
        command = {"command": "get_queue"}
        return self.send_command(command)
