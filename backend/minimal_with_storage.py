from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import uuid
from datetime import datetime

# In-memory storage
agents = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_json(200, {"status": "healthy"})
        elif self.path == '/api/agents/':
            agent_list = list(agents.values())
            self.send_json(200, agent_list)
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
                    "conversations": 0
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

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print('Backend server running on http://localhost:8000')
    print('API endpoints:')
    print('  GET  /api/health')
    print('  GET  /api/agents/')
    print('  POST /api/agents/')
    server.serve_forever()