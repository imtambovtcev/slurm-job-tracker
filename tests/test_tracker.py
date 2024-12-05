import pytest
from slurm_job_tracker import SlurmJobTracker


@pytest.fixture
def tracker():
    """Fixture to initialize a SlurmJobTracker instance."""
    return SlurmJobTracker()


def test_initialization(tracker):
    """Test that the tracker initializes correctly."""
    assert tracker.interval == 5  # Default from config
    assert tracker.max_jobs == 10
    assert tracker.completed_jobs == {}


def test_submit_task(tracker):
    """Test the task submission functionality."""
    tracker.submit_task("/path/to/workdir", "test_script.sh")
    assert not tracker.submission_queue.empty()
    task = tracker.submission_queue.get()
    assert task == ("/path/to/workdir", "test_script.sh")
