import requests
import json
import logging

from .config import SERVER_HOST, SERVER_PORT, SECRET_TOKEN


def send_command(command):
    """Send a command to the Slurm Job Tracker server."""
    server_url = f"http://{SERVER_HOST}:{SERVER_PORT}"
    headers = {'Content-Type': 'application/json'}
    if SECRET_TOKEN:
        headers['Authorization'] = f"Bearer {SECRET_TOKEN}"
    try:
        response = requests.post(server_url, headers=headers, data=json.dumps(command))
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error communicating with server: {e}")
        return None
