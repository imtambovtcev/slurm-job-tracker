import logging
import threading

from .config import debug_token
from .server import run_server
from .tracker import SlurmJobTracker
from .utils import setup_logging


def main():
    """
    Main function to start the Slurm Job Tracker and HTTP server.

    This function sets up logging, loads the debug token, initializes the SlurmJobTracker,
    and starts the HTTP server in a separate daemon thread. It then starts tracking jobs
    and handles graceful shutdown on a keyboard interrupt.
    """
    """Main function to start the Slurm Job Tracker and HTTP server."""
    setup_logging()
    debug_token()
    tracker = SlurmJobTracker()
    server_thread = threading.Thread(target=run_server, args=(tracker,))
    server_thread.daemon = True  # Ensures the server thread exits with the main thread
    server_thread.start()
    logging.info("Started Slurm Job Tracker.")
    try:
        tracker.track_jobs()
    except KeyboardInterrupt:
        logging.info("Shutting down Slurm Job Tracker.")


if __name__ == "__main__":
    main()
