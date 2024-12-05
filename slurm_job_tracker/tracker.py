import subprocess
import json
import datetime
import time
import threading
from queue import Queue
import logging

from .config import (
    TRACKER_INTERVAL,
    HISTORY_FILE,
    CURRENT_FILE,
    MAX_JOBS,
)
from .utils import setup_logging


class SlurmJobTracker:
    """Class to track and manage Slurm jobs."""

    def __init__(self):
        self.interval = TRACKER_INTERVAL
        self.history_file = HISTORY_FILE
        self.current_file = CURRENT_FILE
        self.max_jobs = MAX_JOBS
        self.old_job_dict = {}
        self.completed_jobs = {}
        self.job_files = {}
        self.submission_queue = Queue()
        self.lock = threading.Lock()

        self.load_history()
        self.load_current_files()

    def load_history(self):
        """Load job history from a file."""
        try:
            with open(self.history_file, "r") as f:
                self.completed_jobs = json.load(f)
            logging.info("Loaded job history.")
        except (FileNotFoundError, json.JSONDecodeError):
            self.completed_jobs = {}
            logging.info("No existing job history found.")

    def load_current_files(self):
        """Load current job data from a file."""
        try:
            with open(self.current_file, "r") as f:
                current_data = json.load(f)
                self.old_job_dict = current_data.get('jobs', {})
                for job_id, job_info in self.old_job_dict.items():
                    self.job_files[job_id] = job_info.get('output_file', "Unknown")
            logging.info("Loaded current job data.")
        except (FileNotFoundError, json.JSONDecodeError):
            logging.info("No existing current job data found.")

    def save_history(self):
        """Save job history to a file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.completed_jobs, f, indent=4)
            logging.info("Saved job history.")
        except Exception as e:
            logging.error(f"Error saving history: {e}")

    def save_current(self, job_dict):
        """Save current job data to a file."""
        try:
            with open(self.current_file, "w") as f:
                json.dump(job_dict, f, indent=4)
            logging.info("Saved current job data.")
        except Exception as e:
            logging.error(f"Error saving current data: {e}")

    def get_current_jobs(self):
        """Retrieve current running jobs from Slurm."""
        try:
            output = subprocess.check_output(
                "squeue -u $USER | awk '{print $1}'", shell=True
            ).decode("utf-8").split("\n")[1:]

            output_time = subprocess.check_output(
                "squeue -u $USER | awk '{print $7}'", shell=True
            ).decode("utf-8").split("\n")[1:]

            current_time = datetime.datetime.now()
            jobs = [
                (
                    job_id,
                    (
                        current_time
                        - datetime.timedelta(seconds=self.time_to_seconds(start_time))
                    ).strftime('%Y-%m-%d %H:%M:%S'),
                )
                for job_id, start_time in zip(output, output_time)
                if len(job_id) > 0
            ]
            return jobs
        except subprocess.CalledProcessError as e:
            logging.error(f"Error retrieving current jobs: {e}")
            return []

    @staticmethod
    def time_to_seconds(time_str):
        """Convert time string to seconds."""
        parts = time_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(parts[0])

    def find_job_file(self, job_id):
        """Find the output file associated with a job ID."""
        if job_id in self.job_files:
            return self.job_files[job_id]
        try:
            logging.info(f"Searching for job file for job ID: {job_id}")
            job_file = subprocess.check_output(
                f"find ~/ -iname *slurm-{job_id}.out", shell=True
            ).decode("utf-8").strip()
            self.job_files[job_id] = job_file
            return job_file
        except subprocess.CalledProcessError:
            return "Unknown"

    def submit_task(self, working_dir, script_name="submit_gpaw_alec.sh"):
        """Add a task to the submission queue."""
        self.submission_queue.put((working_dir, script_name))
        logging.info(f"Task queued: {script_name} in {working_dir}")

    def process_submission_queue(self, running_jobs_count):
        """Process the submission queue and submit jobs."""
        while not self.submission_queue.empty() and running_jobs_count < self.max_jobs:
            working_dir, script_name = self.submission_queue.get()
            try:
                logging.info(f"Submitting task: {script_name} in {working_dir}")
                subprocess.run(
                    ["sbatch", script_name], cwd=working_dir, check=True
                )
                running_jobs_count += 1
            except subprocess.CalledProcessError as e:
                logging.error(f"Error submitting task {script_name} in {working_dir}: {e}")
        return running_jobs_count

    def handle_command(self, command):
        """Handle incoming commands from the server."""
        with self.lock:
            if command['command'] == 'submit_task':
                args = command.get('args', {})
                working_dir = args.get('working_dir')
                script_name = args.get('script_name', 'submit_gpaw_alec.sh')
                self.submit_task(working_dir, script_name)
                return {'status': 'Task submitted'}
            elif command['command'] == 'get_status':
                return {'running_jobs': list(self.old_job_dict.keys())}
            else:
                return {'status': 'Unknown command'}

    def track_jobs(self):
        """Main loop to track jobs."""
        while True:
            job_dict = {'timestamp': str(datetime.datetime.now()), 'jobs': {}}
            current_jobs = self.get_current_jobs()

            logging.info('-----\nNow running:\n-----')
            for job_id, start_time in current_jobs:
                if job_id in self.old_job_dict:
                    job_file = self.old_job_dict[job_id].get('output_file', "Unknown")
                    start_time = self.old_job_dict[job_id].get('start_time', start_time)
                else:
                    job_file = self.find_job_file(job_id)

                job_dict['jobs'][job_id] = {
                    'start_time': start_time,
                    'output_file': job_file
                }
                logging.info(f'{job_id} - {start_time} -> {job_file}')

            self.save_current(job_dict)

            current_job_ids = set(job_dict['jobs'].keys())
            previous_job_ids = set(self.old_job_dict.keys())

            finished_jobs = previous_job_ids - current_job_ids
            new_jobs = current_job_ids - previous_job_ids

            for job_id in finished_jobs:
                self.completed_jobs[job_id] = {
                    'start_time': self.old_job_dict[job_id]['start_time'],
                    'end_time': job_dict['timestamp'],
                    'output_file': self.old_job_dict[job_id]['output_file']
                }
                logging.info(f"Job finished: {job_id}")

            for job_id in new_jobs:
                logging.info(f"New job detected: {job_id}")

            self.save_history()

            self.old_job_dict = job_dict['jobs']

            running_jobs_count = len(current_job_ids)
            running_jobs_count = self.process_submission_queue(running_jobs_count)

            time.sleep(self.interval)
