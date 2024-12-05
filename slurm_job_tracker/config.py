import os

# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

# Authentication token (optional)
SECRET_TOKEN = os.getenv('SLURM_TRACKER_TOKEN', '')

# Tracker configuration
TRACKER_INTERVAL = 5  # Interval in seconds
MAX_JOBS = 10

# File paths
HISTORY_FILE = 'slurm_jobs_history.json'
CURRENT_FILE = 'slurm_jobs_current.json'
