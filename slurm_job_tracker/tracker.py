import datetime
import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import timedelta
from queue import Queue

from .config import CURRENT_FILE, HISTORY_FILE, MAX_JOBS, TRACKER_INTERVAL
from .utils import setup_logging


class SlurmJobTracker:
    """
    Class to track and manage Slurm jobs.

    Attributes:
        interval (int): Interval in seconds for tracking jobs.
        history_file (str): Path to the file where job history is stored.
        current_file (str): Path to the file where current job data is stored.
        max_jobs (int): Maximum number of jobs to track.
        completed_jobs (dict): Dictionary to store completed job information.
        job_files (dict): Dictionary to store current job information.
        submission_queue (Queue): Queue to manage job submissions.
        lock (threading.Lock): Lock to ensure thread safety.

    Methods:
        __init__(): Initializes the SlurmJobTracker instance.
        load_history(): Loads job history from a file.
        load_current_files(): Loads current job data from a file.
        save_history(): Saves job history to a file.
        save_current(job_dict): Saves current job data to a file.
        get_current_jobs(): Retrieves current running jobs from Slurm.
        time_to_seconds(time_str): Converts a time string to seconds, supporting days.
        find_job_file(job_id, directory=None, max_search_time=10): Finds the output file associated with a job ID within a time limit.
        submit_task(working_dir, script_name="submit.sh"): Adds a task to the submission queue.
        process_submission_queue(running_jobs_count): Processes the submission queue and submits jobs.
        handle_command(command): Handles incoming commands from the server.
        track_jobs(): Main loop to track jobs.
        is_slurm_reason(reason): Checks if the string from NODELIST(REASON) is a Slurm reason or a node name.
    """

    def __init__(self):
        self.interval = TRACKER_INTERVAL
        self.history_file = HISTORY_FILE
        self.current_file = CURRENT_FILE
        self.max_jobs = MAX_JOBS
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
                job_dict = current_data.get('jobs', {})
                for job_id, job_info in job_dict.items():
                    self.job_files[job_id] = {
                        'directory': job_info.get('directory', None),
                        'filename': job_info.get('filename', None),
                        'start_time': job_info.get('start_time', None),
                        'nodelist': job_info.get('nodelist', None),
                    }
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
        """Retrieve current running jobs from Slurm using standard library."""
        try:
            output = subprocess.check_output(
                ["squeue", "-u", os.getenv("USER")]).decode("utf-8")
            lines = output.strip().split("\n")
            if len(lines) < 2:
                logging.warning("No jobs found in squeue output.")
                return []

            header, *rows = lines
            header_columns = header.split()
            time_index = header_columns.index("TIME")
            job_id_index = header_columns.index("JOBID")
            nodelist_index = header_columns.index("NODELIST(REASON)")

            current_jobs = []
            for row in rows:
                columns = row.split()
                job_id = columns[job_id_index]
                start_time = columns[time_index] if len(
                    columns) > time_index else ""
                nodelist = columns[nodelist_index] if len(
                    columns) > nodelist_index else ""

                if start_time.strip():
                    current_time = datetime.datetime.now()
                    running_time = self.time_to_seconds(start_time)
                    start_timestamp = (current_time - datetime.timedelta(seconds=running_time)).strftime(
                        '%Y-%m-%d %H:%M:%S') if running_time > 0 else None
                    current_jobs.append((job_id, start_timestamp, nodelist))
                else:
                    logging.warning(
                        f"Missing time for job {job_id}, skipping.")

            return current_jobs
        except subprocess.CalledProcessError as e:
            logging.error(f"Error retrieving current jobs: {e}")
            return []
        except ValueError as e:
            logging.error(f"Error parsing squeue output: {e}")
            return []

    @staticmethod
    def time_to_seconds(time_str):
        """Convert time string to seconds, supporting days."""
        try:
            if "-" in time_str:
                days, time_part = time_str.split("-")
                days_in_seconds = int(days) * 86400
            else:
                time_part = time_str
                days_in_seconds = 0

            parts = time_part.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return days_in_seconds + hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                hours, minutes = map(int, parts)
                return days_in_seconds + hours * 3600 + minutes * 60
            else:
                return days_in_seconds + int(parts[0])
        except ValueError as e:
            logging.error(f"Error parsing time string '{time_str}': {e}")
            return 0

    def find_job_file(self, job_id, directory=None, max_search_time=10):
        """Find the output file associated with a job ID with a time limit."""
        if job_id in self.job_files:
            return self.job_files[job_id]

        try:
            logging.info(f"Searching for job file for job ID: {job_id}")

            if directory is None:
                find_command = f"timeout {max_search_time} find ~/ -iname *slurm-{job_id}.out"
            else:
                find_command = f"timeout {max_search_time} find {directory} -maxdepth 1 -iname *slurm-{job_id}.out"

            job_file = subprocess.check_output(
                find_command, shell=True).decode("utf-8").strip()

            if job_file:
                directory, filename = os.path.split(job_file)
                self.job_files[job_id] = {
                    'directory': directory, 'filename': filename}
                return {'directory': directory, 'filename': filename}
            else:
                return {'directory': None, 'filename': None}
        except subprocess.CalledProcessError:
            logging.warning(f"Search for job ID {job_id} timed out or failed.")
            return {'directory': None, 'filename': None}

    def submit_task(self, working_dir, script_name="submit.sh"):
        """Add a task to the submission queue."""
        self.submission_queue.put((working_dir, script_name))
        logging.info(f"Task queued: {script_name} in {working_dir}")

    def process_submission_queue(self, running_jobs_count):
        """Process the submission queue and submit jobs."""
        initial_queue_size = self.submission_queue.qsize()

        logging.info(
            f"Processing submission queue: {initial_queue_size} tasks in the queue.")

        tasks_processed = 0

        while not self.submission_queue.empty():
            if running_jobs_count >= self.max_jobs:
                logging.info(f"Maximum job limit reached ({self.max_jobs}).")
                break

            working_dir, script_name = self.submission_queue.get()

            if not os.path.exists(working_dir):
                logging.error(
                    f"Working directory does not exist: {working_dir}")
                continue

            script_path = os.path.join(working_dir, script_name)
            if not os.path.isfile(script_path):
                logging.error(f"Script not found: {script_path}")
                continue

            try:
                logging.info(
                    f"Submitting task: {script_name} from {working_dir}")
                result = subprocess.run(
                    ["sbatch", script_name],
                    cwd=working_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
                output = result.stdout.strip()
                match = re.search(r"Submitted batch job (\d+)", output)
                if match:
                    job_id = match.group(1)
                    logging.info(
                        f"Task {job_id} submitted successfully with message: {result.stdout.strip()}")
                    running_jobs_count += 1
                    tasks_processed += 1
                    self.job_files[job_id] = {
                        'directory': working_dir, 'filename': f"slurm-{job_id}.out"}
                else:
                    logging.error(
                        f"Failed to submit task {script_name} from {working_dir}: {output}")

            except subprocess.CalledProcessError as e:
                logging.error(
                    f"Failed to submit task {script_name} from {working_dir}: {e.stderr.strip() if e.stderr else str(e)}")
            except Exception as e:
                logging.error(
                    f"Unexpected error while submitting task {script_name} from {working_dir}: {e}")

        remaining_tasks = self.submission_queue.qsize()
        logging.info(
            f"Submission queue processing complete. {remaining_tasks} tasks remain in the queue. {tasks_processed} tasks processed.")

        return remaining_tasks

    def handle_command(self, command):
        """Handle incoming commands from the server."""
        with self.lock:
            if command['command'] == 'submit_task':
                args = command.get('args', {})
                working_dir = args.get('working_dir')
                script_name = args.get('script_name', 'submit_gpaw_alec.sh')
                self.submit_task(working_dir, script_name)
                return {'status': 'Task added to queue'}

            elif command['command'] == 'get_status':
                return {'running_jobs': list(self.job_files.keys())}

            elif command['command'] == 'get_queue':
                queue_contents = list(self.submission_queue.queue)
                return {
                    'status': 'Queue retrieved',
                    'queued_tasks': [
                        {'working_dir': task[0], 'script_name': task[1]}
                        for task in queue_contents
                    ]
                }

            else:
                return {'status': 'Unknown command'}

    def track_jobs(self):
        """Main loop to track jobs."""
        while True:
            job_dict = {'timestamp': str(datetime.datetime.now()), 'jobs': {}}
            # expected to return (job_id, running_time, nodelist)
            current_jobs = self.get_current_jobs()
            running_string = ''

            for job_id, new_start_time, new_nodelist in current_jobs:

                # If we have old job info
                if job_id in self.job_files:
                    job_info = self.job_files[job_id]
                    old_start_time = job_info.get('start_time', None)

                    # Determine final start_time: keep old if not None, else use new
                    final_start_time = old_start_time if old_start_time is not None else new_start_time

                    # If the job is in a reason state, skip searching for the file
                    if self.is_slurm_reason(new_nodelist):
                        logging.info(
                            f'Job {job_id} is in a reason state and not assigned to a node, skipping file search.')
                        job_dict['jobs'][job_id] = {
                            'start_time': final_start_time,
                            'directory': job_info.get('directory'),
                            'filename': job_info.get('filename'),
                            'nodelist': new_nodelist
                        }
                    else:
                        # Not in reason state
                        if job_info.get('filename'):
                            # Already have the filename
                            job_dict['jobs'][job_id] = {
                                'start_time': final_start_time,
                                'directory': job_info.get('directory'),
                                'filename': job_info.get('filename'),
                                'nodelist': new_nodelist
                            }
                        else:
                            # Need to find the file
                            job_file = self.find_job_file(job_id)
                            job_dict['jobs'][job_id] = {
                                'start_time': final_start_time,
                                'directory': job_file['directory'],
                                'filename': job_file['filename'],
                                'nodelist': new_nodelist
                            }

                else:
                    # This is a newly detected job
                    # For new jobs, if start_time wasn't previously set, we rely on new_start_time
                    final_start_time = new_start_time

                    if self.is_slurm_reason(new_nodelist):
                        logging.info(
                            f'Job {job_id} is in a reason state, skipping file search.')
                        job_dict['jobs'][job_id] = {
                            'start_time': final_start_time,
                            'directory': None,
                            'filename': None,
                            'nodelist': new_nodelist
                        }
                    else:
                        # Attempt to find the file for a new running job
                        job_file = self.find_job_file(job_id)
                        job_dict['jobs'][job_id] = {
                            'start_time': final_start_time,
                            'directory': job_file['directory'],
                            'filename': job_file['filename'],
                            'nodelist': new_nodelist
                        }

                # Construct the running string for logging
                job_info_current = job_dict['jobs'][job_id]
                running_string += (f"{job_id} - {job_info_current['start_time']} -> "
                                   f"{job_info_current['directory']}/{job_info_current['filename']} "
                                   f"(Node: {job_info_current['nodelist']})\n")

            logging.info('\n-----Now running:-----\n' +
                         running_string + '\n-----------------------')
            self.save_current(job_dict)

            current_job_ids = set(job_dict['jobs'].keys())
            previous_job_ids = set(self.job_files.keys())

            # Determine which jobs finished and which are new
            finished_jobs = previous_job_ids - current_job_ids
            new_jobs = current_job_ids - previous_job_ids

            # Log finished jobs
            for job_id in finished_jobs:
                self.completed_jobs[job_id] = {
                    'start_time': self.job_files[job_id]['start_time'],
                    'end_time': job_dict['timestamp'],
                    'directory': self.job_files[job_id]['directory'],
                    'filename': self.job_files[job_id]['filename'],
                    'nodelist': self.job_files[job_id].get('nodelist', None)
                }
                logging.info(f"Job finished: {job_id}")

            # Log newly detected jobs
            for job_id in new_jobs:
                logging.info(f"New job detected: {job_id}")

            self.save_history()
            self.job_files = job_dict['jobs']

            running_jobs_count = len(current_job_ids)
            queued_tasks = self.process_submission_queue(running_jobs_count)

            if queued_tasks > 0:
                logging.info(
                    f"{queued_tasks} tasks queued, waiting for job slots to free up.")

            time.sleep(self.interval)

    @staticmethod
    def is_slurm_reason(reason):
        """ Checks if the ftirng from NODELIST(REASON) is a slurm reason or a node name """
        return reason is None or reason == '' or (reason.startswith('(') and reason.endswith(')'))
