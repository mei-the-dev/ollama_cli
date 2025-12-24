#!/usr/bin/env python3
import http.server
import os
import socketserver


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files from the 'test-artifacts' directory
        self.directory = "/path/to/test-artifacts"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


# Set the port number for the server
PORT = 8000


def run(server_class=http.server.HTTPServer, handler_class=MyHttpRequestHandler):
    # Change the working directory to where the script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Create an HTTP server instance
    server_address = ("", PORT)
    httpd = server_class(server_address, handler_class)

    print(f"Serving at port {PORT}")
    # Start the server
    httpd.serve_forever()


if __name__ == "__main__":
    run()
