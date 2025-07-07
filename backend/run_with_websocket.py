#!/usr/bin/env python3
"""Backend with WebSocket support for voice calls"""
import asyncio
import json
import uuid
import os
import sys
from datetime import datetime
from aiohttp import web
import aiohttp_cors

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

# Routes
async def health(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "backend": "run_with_websocket",
        "timestamp": datetime.now().isoformat(),
        "has_gemini_key": bool(os.environ.get('GEMINI_API_KEY')),
        "has_deepgram_key": bool(os.environ.get('DEEPGRAM_API_KEY')),
        "has_elevenlabs_key": bool(os.environ.get('ELEVENLABS_API_KEY'))
    })

async def get_agents(request):
    """Get all agents"""
    return web.json_response(list(agents_db.values()))

async def get_agent(request):
    """Get specific agent"""
    agent_id = request.match_info['agent_id']
    if agent_id in agents_db:
        return web.json_response(agents_db[agent_id])
    return web.json_response({"error": "Agent not found"}, status=404)

async def create_agent(request):
    """Create new agent"""
    try:
        data = await request.json()
        
        # Generate IDs
        agent_id = str(uuid.uuid4())
        agent_display_id = f"{data.get('name', 'Untitled').replace(' ', '-')}-{agent_id[:8]}"
        
        # Create agent with default values
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
        
        # Store agent
        agents_db[agent_id] = new_agent
        print(f"Created agent: {agent_id}", flush=True)
        
        return web.json_response(new_agent)
    except Exception as e:
        print(f"Error creating agent: {e}", flush=True)
        return web.json_response({"error": str(e)}, status=400)

async def update_agent(request):
    """Update existing agent"""
    agent_id = request.match_info['agent_id']
    
    if agent_id not in agents_db:
        return web.json_response({"error": "Agent not found"}, status=404)
    
    try:
        data = await request.json()
        
        # Update agent
        existing_agent = agents_db[agent_id]
        for key, value in data.items():
            if key not in ['id', 'agent_id', 'created_at']:
                existing_agent[key] = value
        
        # Update timestamp
        existing_agent["updated_at"] = datetime.now().isoformat()
        
        # If name changed, update agent_id
        if "name" in data:
            existing_agent["agent_id"] = f"{data['name'].replace(' ', '-')}-{agent_id[:8]}"
        
        return web.json_response(existing_agent)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def delete_agent(request):
    """Delete agent"""
    agent_id = request.match_info['agent_id']
    
    if agent_id in agents_db:
        del agents_db[agent_id]
        return web.json_response({"message": "Agent deleted successfully"})
    return web.json_response({"error": "Agent not found"}, status=404)

async def websocket_handler(request):
    """Handle WebSocket connections for voice calls"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    agent_id = request.match_info.get('agent_id', 'unknown')
    print(f"WebSocket connection opened for agent: {agent_id}", flush=True)
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # Echo back any text messages (placeholder for real voice processing)
                await ws.send_str(json.dumps({
                    "type": "echo",
                    "data": msg.data,
                    "timestamp": datetime.now().isoformat()
                }))
            elif msg.type == aiohttp.WSMsgType.BINARY:
                # Handle binary audio data (placeholder)
                print(f"Received {len(msg.data)} bytes of audio", flush=True)
                # In a real implementation, this would process audio through STT/TTS
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}', flush=True)
    except Exception as e:
        print(f"WebSocket handler error: {e}", flush=True)
    finally:
        print(f"WebSocket connection closed for agent: {agent_id}", flush=True)
    
    return ws

async def audio_upload(request):
    """Handle audio file uploads"""
    try:
        data = await request.post()
        audio_file = data.get('audio')
        
        if not audio_file:
            return web.json_response({"error": "No audio file provided"}, status=400)
        
        # In a real implementation, this would save and process the audio
        filename = f"audio_{datetime.now().timestamp()}.webm"
        
        return web.json_response({
            "filename": filename,
            "size": len(audio_file.file.read()) if hasattr(audio_file, 'file') else 0,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Audio upload error: {e}", flush=True)
        return web.json_response({"error": str(e)}, status=500)

# Create aiohttp application
app = web.Application()

# Configure CORS
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods="*"
    )
})

# Add routes
app.router.add_get('/api/health', health)
app.router.add_get('/api/agents/', get_agents)
app.router.add_get('/api/agents/{agent_id}', get_agent)
app.router.add_post('/api/agents/', create_agent)
app.router.add_put('/api/agents/{agent_id}', update_agent)
app.router.add_delete('/api/agents/{agent_id}', delete_agent)
app.router.add_get('/ws', websocket_handler)
app.router.add_get('/ws/{agent_id}', websocket_handler)
app.router.add_post('/api/audio/upload', audio_upload)

# Apply CORS to all routes
for route in list(app.router.routes()):
    if not isinstance(route.resource, web.StaticResource):
        cors.add(route)

# Initialize agents on startup
async def on_startup(app):
    init_default_agents()
    print(f"Initialized with {len(agents_db)} default agents", flush=True)

app.on_startup.append(on_startup)

if __name__ == '__main__':
    print("Starting WebSocket-enabled server on port 8000...", flush=True)
    web.run_app(app, host='0.0.0.0', port=8000, print=lambda x: None)
    print("Server is ready to handle requests", flush=True)