#!/usr/bin/env python3
"""HTTP-only backend that handles agent CRUD but not WebSocket"""
import sys
import os
import json
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print("NOTE: This backend does not support WebSocket connections for voice calls", flush=True)

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
            "knowledge_resources": 0,
            "status": "active"
        }
        
        agents_db[agent_id] = agent

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        response = json.dumps(data)
        self.wfile.write(response.encode('utf-8'))
    
    def read_json_body(self):
        """Read and parse JSON from request body"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return None, "No request body"
            
            body = self.rfile.read(content_length)
            body_str = body.decode('utf-8')
            data = json.loads(body_str)
            return data, None
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return None, str(e)
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/api/health':
            self.send_json(200, {
                "status": "healthy",
                "backend": "run_http_only",
                "timestamp": datetime.now().isoformat(),
                "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
                "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
                "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY')),
                "websocket_support": False,
                "note": "WebSocket not supported in this deployment. Voice calls will not work."
            })
        elif path == '/api/agents/' or path == '/api/agents':
            agents_list = list(agents_db.values())
            self.send_json(200, agents_list)
        elif path.startswith('/api/agents/') and len(path.split('/')) == 4:
            agent_id = path.split('/')[-1]
            if agent_id in agents_db:
                self.send_json(200, agents_db[agent_id])
            else:
                self.send_json(404, {"error": "Agent not found"})
        elif path == '/ws':
            # WebSocket upgrade request - return informative error
            self.send_json(503, {
                "error": "WebSocket not available", 
                "message": "Voice calls are temporarily unavailable. Agent management features are fully functional.",
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        if path == '/api/agents/' or path == '/api/agents':
            data, error = self.read_json_body()
            if error:
                self.send_json(400, {"error": error})
                return
            
            agent_id = str(uuid.uuid4())
            agent_display_id = f"{data.get('name', 'Untitled').replace(' ', '-')}-{agent_id[:8]}"
            
            new_agent = {
                "id": agent_id,
                "agent_id": agent_display_id,
                "name": data.get('name', 'Untitled Agent'),
                "voice": data.get('voice', 'Vincent'),
                "speed": data.get('speed', '1.0x'),
                "greeting": data.get('greeting', ''),
                "system_prompt": data.get('system_prompt', ''),
                "behavior": data.get('behavior', 'professional'),
                "llm_model": data.get('llm_model', 'GPT 4o'),
                "custom_knowledge": data.get('custom_knowledge', ''),
                "guardrails_enabled": data.get('guardrails_enabled', False),
                "current_date_enabled": data.get('current_date_enabled', True),
                "caller_info_enabled": data.get('caller_info_enabled', True),
                "timezone": data.get('timezone', '(GMT-08:00) Pacific Time (US & Canada)'),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "conversations": 0,
                "minutes_spoken": 0.0,
                "knowledge_resources": 0,
                "status": "active"
            }
            
            agents_db[agent_id] = new_agent
            self.send_json(200, new_agent)
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urlparse(self.path).path
        
        if path.startswith('/api/agents/') and len(path.split('/')) == 4:
            agent_id = path.split('/')[-1]
            
            if agent_id in agents_db:
                data, error = self.read_json_body()
                if error:
                    self.send_json(400, {"error": error})
                    return
                
                existing_agent = agents_db[agent_id]
                for key, value in data.items():
                    if key not in ['id', 'agent_id', 'created_at']:
                        existing_agent[key] = value
                
                existing_agent["updated_at"] = datetime.now().isoformat()
                
                if "name" in data:
                    existing_agent["agent_id"] = f"{data['name'].replace(' ', '-')}-{agent_id[:8]}"
                
                self.send_json(200, existing_agent)
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Log HTTP requests"""
        print(f"{self.address_string()} - {format % args}", flush=True)

if __name__ == '__main__':
    init_default_agents()
    print(f"Initialized with {len(agents_db)} default agents", flush=True)
    
    print("Starting HTTP-only server on port 8000...", flush=True)
    print("WARNING: Voice calls will not work without WebSocket support", flush=True)
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print("Server is ready to handle requests", flush=True)
    server.serve_forever()