#!/usr/bin/env python3
"""
preview.py - A lightweight local server for the Frontend Design Skill.

Allows OpenPango agents to quickly serve their generated HTML/CSS/JS or 
static build directories on a predictable port, so the Browser skill can 
visually verify the aesthetic output against the prompt requirements.
"""

import http.server
import socketserver
import os
import sys
import threading
import time

PORT = 8080

class PreviewServer:
    def __init__(self, directory: str, port: int = PORT):
        self.directory = os.path.abspath(directory)
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        """Starts the server in a daemon thread."""
        if not os.path.exists(self.directory):
            print(f"Error: Directory {self.directory} does not exist.")
            return False

        # Change to the target directory to serve its contents
        os.chdir(self.directory)
        
        Handler = http.server.SimpleHTTPRequestHandler
        # Allow reusing address to prevent "Address already in use" errors during agent iterations
        socketserver.TCPServer.allow_reuse_address = True
        
        try:
            self.httpd = socketserver.TCPServer(("", self.port), Handler)
            print(f"Serving at http://localhost:{self.port} from {self.directory}")
            
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            return True
        except OSError as e:
            print(f"Failed to start server on port {self.port}: {e}")
            return False

    def stop(self):
        """Stops the server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("Preview server stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start a local preview server for frontend verification.")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to serve (default: current)")
    parser.add_argument("-p", "--port", type=int, default=PORT, help="Port to serve on")
    args = parser.parse_args()

    server = PreviewServer(args.directory, args.port)
    if server.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
            sys.exit(0)
    else:
        sys.exit(1)
