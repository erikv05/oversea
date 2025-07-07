#!/usr/bin/env python3
"""Minimal WebSocket server that responds to voice calls"""
import asyncio
import websockets
import json
import os
from datetime import datetime

print("Starting minimal WebSocket server...", flush=True)

async def echo(websocket, path):
    """Simple WebSocket echo handler"""
    print(f"New WebSocket connection from {websocket.remote_address} on path: {path}", flush=True)
    
    try:
        # Send initial connection message
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        }))
        
        async for message in websocket:
            print(f"Received: {message[:100]}...", flush=True)
            
            # Try to parse as JSON
            try:
                data = json.loads(message)
                if data.get("type") == "agent_config":
                    # Acknowledge agent configuration
                    await websocket.send(json.dumps({
                        "type": "config_received",
                        "agent_id": data.get("agent_id"),
                        "timestamp": datetime.now().isoformat()
                    }))
                else:
                    # Echo back
                    await websocket.send(json.dumps({
                        "type": "echo",
                        "original": message,
                        "timestamp": datetime.now().isoformat()
                    }))
            except:
                # Not JSON, probably binary audio - just acknowledge
                await websocket.send(json.dumps({
                    "type": "audio_received",
                    "size": len(message),
                    "timestamp": datetime.now().isoformat()
                }))
                
    except websockets.exceptions.ConnectionClosed:
        print(f"WebSocket connection closed", flush=True)
    except Exception as e:
        print(f"WebSocket error: {e}", flush=True)

# Start server on port 8000 (nginx expects this)
start_server = websockets.serve(echo, "0.0.0.0", 8000, 
                               process_request=lambda path, headers: (200, [], b"OK\n") if path == "/api/health" else None)

print("WebSocket server starting on port 8000...", flush=True)
asyncio.get_event_loop().run_until_complete(start_server)
print("WebSocket server is running", flush=True)
asyncio.get_event_loop().run_forever()