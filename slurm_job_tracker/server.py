import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import SECRET_TOKEN, SERVER_HOST, SERVER_PORT, mask_token
from .tracker import SlurmJobTracker


class CommandHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Slurm Job Tracker commands."""

    def do_POST(self):
        # Debug: Check the incoming headers
        masked_headers = {key: (f"Bearer {mask_token(value.split()[-1])}" if key == "Authorization" else value) 
                        for key, value in self.headers.items()}
        logging.info(f"Received headers (masked): {masked_headers}")

        # Check the Authorization header
        auth_header = self.headers.get('Authorization')
        masked_auth_header = f"Bearer {mask_token(auth_header.split()[-1])}" if auth_header else "None"
        logging.info(f"Authorization header received (masked): {masked_auth_header}")

        if not SECRET_TOKEN:
            logging.error("SECRET_TOKEN is not set on the server!")
            self.send_response(500)  # Internal Server Error
            self.end_headers()
            self.wfile.write(b"Server misconfigured: SECRET_TOKEN is not set.")
            return

        if not auth_header or auth_header != f"Bearer {SECRET_TOKEN}":
            logging.warning("Unauthorized access attempt detected!")
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
