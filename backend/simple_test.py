from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "backend": "simple_test"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    print("Starting simple test server on port 8000...")
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    server.serve_forever()