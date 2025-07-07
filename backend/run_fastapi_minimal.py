#!/usr/bin/env python3
"""Minimal FastAPI backend with WebSocket support"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import os
from datetime import datetime

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

# Initialize agents
init_default_agents()

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "backend": "run_fastapi_minimal",
        "timestamp": datetime.now().isoformat(),
        "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
        "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
        "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY'))
    }

@app.get("/api/agents/")
async def get_agents():
    return list(agents_db.values())

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    if agent_id in agents_db:
        return agents_db[agent_id]
    return {"error": "Agent not found"}

@app.post("/api/agents/")
async def create_agent(agent_data: dict):
    agent_id = str(uuid.uuid4())
    agent_display_id = f"{agent_data.get('name', 'Untitled').replace(' ', '-')}-{agent_id[:8]}"
    
    new_agent = {
        "id": agent_id,
        "agent_id": agent_display_id,
        "name": agent_data.get('name', 'Untitled Agent'),
        "voice": agent_data.get('voice', 'Vincent'),
        "speed": agent_data.get('speed', '1.0x'),
        "greeting": agent_data.get('greeting', ''),
        "system_prompt": agent_data.get('system_prompt', ''),
        "behavior": agent_data.get('behavior', 'professional'),
        "llm_model": agent_data.get('llm_model', 'GPT 4o'),
        "custom_knowledge": agent_data.get('custom_knowledge', ''),
        "guardrails_enabled": agent_data.get('guardrails_enabled', False),
        "current_date_enabled": agent_data.get('current_date_enabled', True),
        "caller_info_enabled": agent_data.get('caller_info_enabled', True),
        "timezone": agent_data.get('timezone', '(GMT-08:00) Pacific Time (US & Canada)'),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "conversations": 0,
        "minutes_spoken": 0.0,
        "knowledge_resources": 0,
        "status": "active"
    }
    
    agents_db[agent_id] = new_agent
    return new_agent

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket connection opened", flush=True)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            print(f"WebSocket received: {data[:100]}", flush=True)
            
            # Parse and handle message
            try:
                message = json.loads(data)
                
                if message.get("type") == "agent_config":
                    # Agent configuration received
                    await websocket.send_json({
                        "type": "config_received",
                        "agent_id": message.get("agent_id"),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    # Echo other messages
                    await websocket.send_json({
                        "type": "echo",
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except json.JSONDecodeError:
                # Handle non-JSON messages (e.g., binary audio)
                await websocket.send_json({
                    "type": "received",
                    "size": len(data),
                    "timestamp": datetime.now().isoformat()
                })
                
    except Exception as e:
        print(f"WebSocket error: {e}", flush=True)
    finally:
        print(f"WebSocket connection closed", flush=True)

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server with WebSocket support...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")