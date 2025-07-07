#!/usr/bin/env python3
"""Direct runner that starts the simple test server immediately"""
import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "status": "healthy",
                "backend": "run_direct",
                "timestamp": "2025-07-07T21:00:00Z",
                "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
                "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
                "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY'))
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/api/agents/':
            # Return default agents
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            agents = [
                {
                    "id": "agent-1",
                    "agent_id": "Bozidar-agent-1",
                    "name": "Bozidar",
                    "voice": "Vincent",
                    "speed": "1.0x",
                    "greeting": "Hello! I'm Bozidar. How can I help you today?",
                    "system_prompt": "You are Bozidar, a helpful and professional assistant.",
                    "behavior": "professional",
                    "llm_model": "GPT 4o",
                    "custom_knowledge": "",
                    "guardrails_enabled": False,
                    "current_date_enabled": True,
                    "caller_info_enabled": True,
                    "timezone": "(GMT-08:00) Pacific Time (US & Canada)",
                    "created_at": "2025-07-07T20:00:00",
                    "updated_at": "2025-07-07T20:00:00",
                    "conversations": 3,
                    "minutes_spoken": 1.1,
                    "knowledge_resources": 0
                }
            ]
            self.wfile.write(json.dumps(agents).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}", flush=True)

if __name__ == '__main__':
    print("Starting direct server on port 8000...", flush=True)
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print("Server is ready to handle requests", flush=True)
    server.serve_forever()