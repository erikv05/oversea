#!/usr/bin/env python3
"""Combined HTTP and WebSocket backend using FastAPI"""
import sys
import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional

print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)

# Import FastAPI components
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError as e:
    print(f"Error importing FastAPI: {e}", flush=True)
    print("Please ensure fastapi and uvicorn are installed", flush=True)
    sys.exit(1)

# In-memory storage for agents
agents_db: Dict[str, dict] = {}

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
        print(f"Initialized agent: {agent['name']} with ID {agent_id}", flush=True)

# Initialize agents on module load
init_default_agents()

# Create FastAPI app
app = FastAPI(title="Voice Agent Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "backend": "run_combined",
        "timestamp": datetime.now().isoformat(),
        "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
        "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
        "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY')),
        "websocket_support": True,
        "agents_count": len(agents_db)
    }

# Get all agents
@app.get("/api/agents/")
@app.get("/api/agents")
async def get_agents():
    """Get all agents"""
    return list(agents_db.values())

# Get specific agent
@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get specific agent by ID"""
    if agent_id in agents_db:
        return agents_db[agent_id]
    raise HTTPException(status_code=404, detail="Agent not found")

# Create new agent
@app.post("/api/agents/")
@app.post("/api/agents")
async def create_agent(agent_data: dict):
    """Create new agent"""
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
    print(f"Created agent: {new_agent['name']} with ID {agent_id}", flush=True)
    return new_agent

# Update agent
@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, agent_data: dict):
    """Update existing agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    existing_agent = agents_db[agent_id]
    
    # Update fields except protected ones
    for key, value in agent_data.items():
        if key not in ['id', 'agent_id', 'created_at']:
            existing_agent[key] = value
    
    # Update timestamp
    existing_agent["updated_at"] = datetime.now().isoformat()
    
    # If name changed, update agent_id
    if "name" in agent_data:
        existing_agent["agent_id"] = f"{agent_data['name'].replace(' ', '-')}-{agent_id[:8]}"
    
    print(f"Updated agent: {agent_id}", flush=True)
    return existing_agent

# Delete agent
@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    del agents_db[agent_id]
    print(f"Deleted agent: {agent_id}", flush=True)
    return {"message": "Agent deleted successfully"}

# WebSocket endpoint for voice calls
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice communication"""
    await websocket.accept()
    client_address = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    print(f"WebSocket connection opened from {client_address}", flush=True)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Receive message - could be text (JSON) or binary (audio)
            message = await websocket.receive()
            
            if "text" in message:
                # Text message - likely JSON control message
                data = message["text"]
                print(f"WebSocket received text: {data[:100]}...", flush=True)
                
                try:
                    parsed = json.loads(data)
                    
                    if parsed.get("type") == "agent_config":
                        # Agent configuration received
                        await websocket.send_json({
                            "type": "config_received",
                            "agent_id": parsed.get("agent_id"),
                            "timestamp": datetime.now().isoformat()
                        })
                        print(f"Agent config received for: {parsed.get('agent_id')}", flush=True)
                    
                    elif parsed.get("type") == "audio":
                        # Audio data in JSON format
                        await websocket.send_json({
                            "type": "audio_received",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    else:
                        # Echo other messages for now
                        await websocket.send_json({
                            "type": "echo",
                            "original": parsed,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                except json.JSONDecodeError:
                    # Not JSON - treat as plain text
                    await websocket.send_json({
                        "type": "text_received",
                        "size": len(data),
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif "bytes" in message:
                # Binary message - likely audio data
                audio_data = message["bytes"]
                print(f"WebSocket received binary audio: {len(audio_data)} bytes", flush=True)
                
                # For now, just acknowledge receipt
                # In a real implementation, this would be sent to STT service
                await websocket.send_json({
                    "type": "audio_received",
                    "size": len(audio_data),
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        print(f"WebSocket connection closed normally from {client_address}", flush=True)
    except Exception as e:
        print(f"WebSocket error from {client_address}: {type(e).__name__}: {e}", flush=True)
    finally:
        print(f"WebSocket cleanup for {client_address}", flush=True)

# Run the server if executed directly
if __name__ == "__main__":
    print(f"Starting combined HTTP/WebSocket server on port 8000...", flush=True)
    print(f"Initialized with {len(agents_db)} agents", flush=True)
    
    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        use_colors=False
    )
    
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except Exception as e:
        print(f"Server error: {e}", flush=True)
        sys.exit(1)