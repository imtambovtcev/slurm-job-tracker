from .utils import setup_logging
from .tracker import SlurmJobTracker
from .server import run_server
import threading
import logging

def main():
    """Main function to start the Slurm Job Tracker and HTTP server."""
    setup_logging()
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
