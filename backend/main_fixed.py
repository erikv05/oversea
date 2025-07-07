"""Voice Agent API - Main Application"""
import asyncio
import os
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Print early debug info
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Environment: CLOUD_RUN={os.environ.get('CLOUD_RUN')}", flush=True)

try:
    from config.settings import CORS_ORIGINS, GEMINI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, MCP_URL
    print("✓ Settings imported successfully", flush=True)
except Exception as e:
    print(f"✗ Failed to import settings: {e}", flush=True)
    CORS_ORIGINS = ["*"]
    GEMINI_API_KEY = ""
    DEEPGRAM_API_KEY = ""
    ELEVENLABS_API_KEY = ""
    MCP_URL = ""

# Initialize FastAPI app
app = FastAPI(title="Voice Agent API", version="2.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Voice Agent API - Fast Response Version", "version": "2.0"}

# Test endpoint
@app.get("/api/test")
def test_endpoint():
    return {"status": "ok", "timestamp": str(datetime.now())}

# Health check endpoints - both paths for compatibility
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "has_gemini_key": bool(GEMINI_API_KEY),
        "has_deepgram_key": bool(DEEPGRAM_API_KEY),
        "has_elevenlabs_key": bool(ELEVENLABS_API_KEY),
        "backend": "main_fixed",
        "timestamp": str(datetime.now())
    }

# Try to import routers
try:
    from routes.audio import router as audio_router
    app.include_router(audio_router)
    print("✓ Audio router loaded", flush=True)
except Exception as e:
    print(f"✗ Failed to load audio router: {e}", flush=True)

try:
    from routes.agents import router as agents_router
    app.include_router(agents_router)
    print("✓ Agents router loaded", flush=True)
except Exception as e:
    print(f"✗ Failed to load agents router: {e}", flush=True)

try:
    from routes.websocket import websocket_endpoint
    app.websocket("/ws")(websocket_endpoint)
    print("✓ WebSocket endpoint loaded", flush=True)
except Exception as e:
    print(f"✗ Failed to load websocket endpoint: {e}", flush=True)

# MCP client global
mcp_client = None

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60, flush=True)
    print("🚀 Voice Agent Server Starting...", flush=True)
    print("="*60, flush=True)
    
    # Try to start cleanup task
    try:
        from utils.cleanup import cleanup_audio_files
        asyncio.create_task(cleanup_audio_files())
        print("✓ Cleanup task started", flush=True)
    except Exception as e:
        print(f"✗ Cleanup task failed: {e}", flush=True)
    
    # Initialize MCP client in background (non-blocking)
    async def init_mcp():
        global mcp_client
        if MCP_URL:
            try:
                print("Initializing MCP client...", flush=True)
                from mcp_client import MCPClient
                mcp_client = MCPClient(MCP_URL)
                await mcp_client.initialize()
                print("✓ MCP client initialized", flush=True)
            except Exception as e:
                print(f"✗ MCP client failed: {e}", flush=True)
                mcp_client = None
    
    # Start MCP initialization in background
    asyncio.create_task(init_mcp())
    
    print("="*60, flush=True)
    print("✓ Server ready", flush=True)
    print("="*60 + "\n", flush=True)

@app.on_event("shutdown")
async def shutdown_event():
    print("\n" + "="*60, flush=True)
    print("👋 Shutting down server...", flush=True)
    # Close MCP client
    global mcp_client
    if mcp_client:
        try:
            await mcp_client.close()
            print("✓ MCP client closed", flush=True)
        except:
            pass
    print("="*60 + "\n", flush=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_fixed:app", host="0.0.0.0", port=8000, log_level="info")