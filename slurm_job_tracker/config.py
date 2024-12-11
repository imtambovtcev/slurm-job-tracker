import os

from dotenv import load_dotenv

load_dotenv()

# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

# Authentication token (optional)
SECRET_TOKEN = os.getenv('SLURM_TRACKER_TOKEN', '')


def mask_token(token, visible_length=4):
    """Mask all but the last `visible_length` characters of the token."""
    if len(token) <= visible_length:
        return token
    return '*' * (len(token) - visible_length) + token[-visible_length:]


def debug_token():
    """Print the masked token for debugging purposes."""
    if SECRET_TOKEN:
        print(f"Loaded SLURM_TRACKER_TOKEN: {mask_token(SECRET_TOKEN)}")
    else:
        print("No SLURM_TRACKER_TOKEN found in environment.")


# Tracker configuration
TRACKER_INTERVAL = 5  # Interval in seconds
MAX_JOBS = 50

# File paths
HISTORY_FILE = 'slurm_jobs_history.json'
CURRENT_FILE = 'slurm_jobs_current.json'
