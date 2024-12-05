from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import threading

from .config import SERVER_HOST, SERVER_PORT, SECRET_TOKEN
from .tracker import SlurmJobTracker


class CommandHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Slurm Job Tracker commands."""

    def do_POST(self):
        # Verify the Authorization header if a secret token is set
        if SECRET_TOKEN:
            auth_header = self.headers.get('Authorization')
            if auth_header != f"Bearer {SECRET_TOKEN}":
                self.send_response(401)  # Unauthorized
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return

        # Process incoming command
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            command = json.loads(post_data)
            response = self.server.tracker.handle_command(command)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except json.JSONDecodeError:
            self.send_response(400)  # Bad Request
            self.end_headers()
            self.wfile.write(b"Invalid JSON")

    def log_message(self, format, *args):
        # Override to use logging instead of printing to stderr
        logging.info("%s - - [%s] %s" % (
            self.client_address[0],
            self.log_date_time_string(),
            format % args,
        ))


class ThreadedHTTPServer(HTTPServer):
    """HTTP server that handles requests in a separate thread."""

    def __init__(self, server_address, RequestHandlerClass, tracker):
        super().__init__(server_address, RequestHandlerClass)
        self.tracker = tracker


def run_server(tracker):
    """Start the HTTP server."""
    server_address = (SERVER_HOST, SERVER_PORT)
    httpd = ThreadedHTTPServer(server_address, CommandHandler, tracker)
    logging.info(f"Server running on http://{SERVER_HOST}:{SERVER_PORT}")
    httpd.serve_forever()
