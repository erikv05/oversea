#!/usr/bin/env python3
"""Simple backend with basic WebSocket support"""
import asyncio
import json
import uuid
import os
import sys
from datetime import datetime
import websockets
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from urllib.parse import urlparse

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

class HTTPHandler(BaseHTTPRequestHandler):
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
                "backend": "run_simple_ws",
                "timestamp": datetime.now().isoformat(),
                "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
                "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
                "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY')),
                "websocket_port": 8001
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
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Log HTTP requests"""
        print(f"HTTP: {self.address_string()} - {format % args}", flush=True)

# WebSocket handler
async def websocket_handler(websocket, path):
    """Handle WebSocket connections"""
    print(f"WebSocket connection opened: {path}", flush=True)
    
    try:
        # Send initial connection message
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Echo messages back
        async for message in websocket:
            print(f"WebSocket received: {message[:100]}", flush=True)
            
            # Echo the message back
            await websocket.send(json.dumps({
                "type": "echo",
                "data": message,
                "timestamp": datetime.now().isoformat()
            }))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"WebSocket connection closed", flush=True)
    except Exception as e:
        print(f"WebSocket error: {e}", flush=True)

async def start_websocket_server():
    """Start WebSocket server on port 8001"""
    print("Starting WebSocket server on port 8001...", flush=True)
    await websockets.serve(websocket_handler, '0.0.0.0', 8001)
    print("WebSocket server ready", flush=True)

def run_http_server():
    """Run HTTP server in a thread"""
    print("Starting HTTP server on port 8000...", flush=True)
    server = HTTPServer(('0.0.0.0', 8000), HTTPHandler)
    print("HTTP server ready", flush=True)
    server.serve_forever()

if __name__ == '__main__':
    # Initialize agents
    init_default_agents()
    print(f"Initialized with {len(agents_db)} default agents", flush=True)
    
    # Start HTTP server in a thread
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Start WebSocket server in main thread
    asyncio.run(start_websocket_server())
    
    # Keep running
    asyncio.get_event_loop().run_forever()