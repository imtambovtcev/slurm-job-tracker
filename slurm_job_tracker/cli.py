import argparse
from slurm_job_tracker.client import SlurmJobTrackerClient

def main():
    parser = argparse.ArgumentParser(description="Slurm Job Tracker Client")
    parser.add_argument("command", choices=["submit", "status", "queue", "info"], help="Command to execute")
    parser.add_argument("--working-dir", help="Working directory for task submission")
    parser.add_argument("--script-name", default="submit.sh", help="Submission script name (default: submit.sh)")
    args = parser.parse_args()

    client = SlurmJobTrackerClient()

    if args.command == "submit":
        if not args.working_dir:
            print("Error: --working-dir is required for the submit command.")
            return
        response = client.submit_task(args.working_dir, args.script_name)
        print("Submission Response:", response)

    elif args.command == "status":
        response = client.get_status()
        print("Current Status:", response)

    elif args.command == "queue":
        response = client.get_queue()
        print("Queue:", response)

    elif args.command == "info":
        response = client.get_info()
        print("Info:", response)
        
    return  # Ensure the function properly exits
