import pytest
from slurm_job_tracker import SlurmJobTracker
from slurm_job_tracker.config import TRACKER_INTERVAL, MAX_JOBS


@pytest.fixture
def tracker():
    """Fixture to initialize a SlurmJobTracker instance."""
    return SlurmJobTracker()

def test_initialization(tracker):
    """Test that the tracker initializes correctly."""
    tracker.completed_jobs = {}  # Clear any preloaded job data
    assert tracker.interval == TRACKER_INTERVAL  # Default from config
    assert tracker.max_jobs == MAX_JOBS         # Default from config
    assert tracker.completed_jobs == {}


def test_submit_task(tracker):
    """Test the task submission functionality."""
    tracker.submit_task("/path/to/workdir", "test_script.sh")
    assert not tracker.submission_queue.empty()
    task = tracker.submission_queue.get()
    assert task == ("/path/to/workdir", "test_script.sh")
