#!/usr/bin/env python3
import http.server
import socketserver

PORT = 8000


# Define a handler that serves files from the current directory and its subdirectories.
class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="test-artifacts", **kwargs)


# Set up an HTTP server to listen on PORT using the handler defined above.
with socketserver.TCPServer(("", PORT), MyHttpRequestHandler) as httpd:
    print(f"Serving at port {PORT}")
    # Serve requests until manually stopped (Ctrl+C).
    httpd.serve_forever()
