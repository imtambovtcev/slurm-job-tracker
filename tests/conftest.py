import os


def pytest_configure():
    """Set environment variables globally for the pytest session."""
    os.environ["SLURM_TRACKER_TOKEN"] = "test_token"
