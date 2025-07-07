import asyncio
import websockets
import json
import http.server
import threading
from datetime import datetime
import uuid

# In-memory storage (shared with HTTP server)
agents = {}

# WebSocket handler
async def websocket_handler(websocket, path):
    print(f"WebSocket connection opened: {path}")
    try:
        async for message in websocket:
            print(f"Received WebSocket message: {message}")
            # Echo back a simple response
            response = {
                "type": "connected",
                "message": "WebSocket connection established",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")

# HTTP Handler
class HTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_json(200, {"status": "healthy"})
        elif self.path == '/api/agents/':
            agent_list = list(agents.values())
            self.send_json(200, agent_list)
        elif self.path.startswith('/api/agents/') and len(self.path.split('/')) == 4:
            agent_id = self.path.split('/')[-1]
            if agent_id in agents:
                self.send_json(200, agents[agent_id])
            else:
                self.send_json(404, {"error": "Agent not found"})
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/agents/':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                agent_id = str(uuid.uuid4())
                
                agent = {
                    "id": agent_id,
                    "agent_id": f"agent-{agent_id[:8]}",
                    "name": data.get("name", "Unnamed Agent"),
                    "voice": data.get("voice", "Vincent"),
                    "speed": data.get("speed", "1.0x"),
                    "greeting": data.get("greeting", ""),
                    "system_prompt": data.get("system_prompt", ""),
                    "behavior": data.get("behavior", "professional"),
                    "llm_model": data.get("llm_model", "GPT 4o"),
                    "custom_knowledge": data.get("custom_knowledge", ""),
                    "guardrails_enabled": data.get("guardrails_enabled", False),
                    "current_date_enabled": data.get("current_date_enabled", True),
                    "caller_info_enabled": data.get("caller_info_enabled", True),
                    "timezone": data.get("timezone", "(GMT-08:00) Pacific Time (US & Canada)"),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "conversations": 0,
                    "minutes_spoken": 0.0,
                    "status": "active"
                }
                
                agents[agent_id] = agent
                self.send_json(200, agent)
                
            except Exception as e:
                self.send_json(400, {"error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        # Suppress HTTP logs
        pass

# Run HTTP server in a thread
def run_http_server():
    server = http.server.HTTPServer(('0.0.0.0', 8000), HTTPHandler)
    print('HTTP server running on http://localhost:8000')
    server.serve_forever()

# Main function
async def main():
    # Start HTTP server in background thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Start WebSocket server
    print('WebSocket server running on ws://localhost:8000')
    async with websockets.serve(websocket_handler, '0.0.0.0', 8001):
        await asyncio.Future()  # Run forever

if __name__ == '__main__':
    print('Starting Voice Agent Backend with WebSocket support...')
    print('API endpoints:')
    print('  GET  /api/health')
    print('  GET  /api/agents/')
    print('  GET  /api/agents/:id')
    print('  POST /api/agents/')
    print('  WS   ws://localhost:8001')
    
    asyncio.run(main())