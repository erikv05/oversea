#!/usr/bin/env python3
"""Full backend with agent CRUD operations - simple HTTP server"""
import sys
import os
import json
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)

# In-memory storage for agents
agents_db = {}

# Initialize with default agents
def init_default_agents():
    """Initialize with default agents"""
    default_agents = [
        {
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
            "conversations": 3,
            "minutes_spoken": 1.1
        },
        {
            "name": "Untitled Agent",
            "voice": "Vincent",
            "speed": "1.0x",
            "greeting": "Hi there! How can I assist you?",
            "system_prompt": "You are a friendly conversational assistant.",
            "behavior": "chatty",
            "llm_model": "GPT 4o",
            "custom_knowledge": "",
            "guardrails_enabled": False,
            "current_date_enabled": True,
            "caller_info_enabled": True,
            "timezone": "(GMT-08:00) Pacific Time (US & Canada)",
            "conversations": 2,
            "minutes_spoken": 0.0
        }
    ]
    
    for agent_data in default_agents:
        agent_id = str(uuid.uuid4())
        agent_display_id = f"{agent_data['name'].replace(' ', '-')}-{agent_id[:8]}"
        
        agent = {
            **agent_data,
            "id": agent_id,
            "agent_id": agent_display_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "knowledge_resources": 0
        }
        
        agents_db[agent_id] = agent

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/api/health':
            self.send_json(200, {
                "status": "healthy",
                "backend": "run_full_simple",
                "timestamp": datetime.now().isoformat(),
                "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
                "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
                "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY'))
            })
        elif path == '/api/agents/' or path == '/api/agents':
            # Return all agents
            agents_list = list(agents_db.values())
            self.send_json(200, agents_list)
        elif path.startswith('/api/agents/') and len(path.split('/')) == 4:
            # Get specific agent
            agent_id = path.split('/')[-1]
            if agent_id in agents_db:
                self.send_json(200, agents_db[agent_id])
            else:
                self.send_json(404, {"error": "Agent not found"})
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        if path == '/api/agents/' or path == '/api/agents':
            # Create new agent
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                try:
                    agent_data = json.loads(body.decode())
                    
                    # Generate IDs
                    agent_id = str(uuid.uuid4())
                    agent_display_id = f"{agent_data.get('name', 'Untitled').replace(' ', '-')}-{agent_id[:8]}"
                    
                    # Create agent
                    new_agent = {
                        **agent_data,
                        "id": agent_id,
                        "agent_id": agent_display_id,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "conversations": 0,
                        "minutes_spoken": 0.0,
                        "knowledge_resources": 0
                    }
                    
                    # Store agent
                    agents_db[agent_id] = new_agent
                    
                    self.send_json(200, new_agent)
                except json.JSONDecodeError:
                    self.send_json(400, {"error": "Invalid JSON"})
            else:
                self.send_json(400, {"error": "No request body"})
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urlparse(self.path).path
        
        if path.startswith('/api/agents/') and len(path.split('/')) == 4:
            agent_id = path.split('/')[-1]
            
            if agent_id in agents_db:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    try:
                        update_data = json.loads(body.decode())
                        
                        # Update agent
                        existing_agent = agents_db[agent_id]
                        for key, value in update_data.items():
                            if key not in ['id', 'agent_id', 'created_at']:
                                existing_agent[key] = value
                        
                        # Update timestamp
                        existing_agent["updated_at"] = datetime.now().isoformat()
                        
                        # If name changed, update agent_id
                        if "name" in update_data:
                            existing_agent["agent_id"] = f"{update_data['name'].replace(' ', '-')}-{agent_id[:8]}"
                        
                        self.send_json(200, existing_agent)
                    except json.JSONDecodeError:
                        self.send_json(400, {"error": "Invalid JSON"})
                else:
                    self.send_json(400, {"error": "No request body"})
            else:
                self.send_json(404, {"error": "Agent not found"})
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        path = urlparse(self.path).path
        
        if path.startswith('/api/agents/') and len(path.split('/')) == 4:
            agent_id = path.split('/')[-1]
            
            if agent_id in agents_db:
                del agents_db[agent_id]
                self.send_json(200, {"message": "Agent deleted successfully"})
            else:
                self.send_json(404, {"error": "Agent not found"})
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Log HTTP requests"""
        print(f"{self.address_string()} - {format % args}", flush=True)

if __name__ == '__main__':
    # Initialize default agents
    init_default_agents()
    print(f"Initialized with {len(agents_db)} default agents", flush=True)
    
    # Start server
    print("Starting full simple server on port 8000...", flush=True)
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print("Server is ready to handle requests", flush=True)
    server.serve_forever()