#!/usr/bin/env python3
import asyncio
from aiohttp import web
import aiohttp
import json
import uuid
from datetime import datetime

# In-memory storage
agents = {}

# HTTP routes
async def health(request):
    return web.json_response({"status": "healthy"})

async def get_agents(request):
    return web.json_response(list(agents.values()))

async def get_agent(request):
    agent_id = request.match_info['id']
    if agent_id in agents:
        return web.json_response(agents[agent_id])
    return web.json_response({"error": "Agent not found"}, status=404)

async def create_agent(request):
    try:
        data = await request.json()
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
        return web.json_response(agent)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

# WebSocket handler
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    print("WebSocket connection opened")
    
    # Send initial connection message
    await ws.send_json({
        "type": "connected",
        "message": "WebSocket connection established",
        "timestamp": datetime.now().isoformat()
    })
    
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            print(f"Received: {msg.data}")
            # Echo back or handle the message
            await ws.send_json({
                "type": "echo",
                "message": msg.data,
                "timestamp": datetime.now().isoformat()
            })
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print(f'WebSocket error: {ws.exception()}')
    
    print('WebSocket connection closed')
    return ws

# Setup application
app = web.Application()

# Add CORS middleware
async def cors_middleware(app, handler):
    async def middleware_handler(request):
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = web.Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        # Handle regular requests
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    return middleware_handler

app.middlewares.append(cors_middleware)

# Add routes
app.router.add_get('/api/health', health)
app.router.add_get('/api/agents/', get_agents)
app.router.add_get('/api/agents/{id}', get_agent)
app.router.add_post('/api/agents/', create_agent)
app.router.add_get('/ws', websocket_handler)

if __name__ == '__main__':
    print('Starting Voice Agent Backend with WebSocket support...')
    print('Server running on http://localhost:8000')
    print('API endpoints:')
    print('  GET  /api/health')
    print('  GET  /api/agents/')
    print('  GET  /api/agents/:id')
    print('  POST /api/agents/')
    print('  WS   ws://localhost:8000/ws')
    
    web.run_app(app, host='0.0.0.0', port=8000)