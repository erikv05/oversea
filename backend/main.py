"""Voice Agent API - Main Application"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import CORS_ORIGINS
from routes.audio import router as audio_router
from routes.websocket import websocket_endpoint
from routes.agents import router as agents_router
from utils.cleanup import cleanup_audio_files
from mcp_client import MCPClient
from config.settings import MCP_URL

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

# Include routers
app.include_router(audio_router)
app.include_router(agents_router)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Voice Agent API - Fast Response Version", "version": "2.0"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

# MCP client global
mcp_client = None


@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("🚀 Voice Agent Server Starting...")
    print("="*60)
    
    # Start cleanup task
    asyncio.create_task(cleanup_audio_files())
    
    # Initialize MCP client if needed
    global mcp_client
    if MCP_URL:
        try:
            mcp_client = MCPClient(MCP_URL)
            await mcp_client.initialize()
            print("✓ MCP client initialized")
        except Exception as e:
            print(f"✗ MCP client failed: {e}")
            mcp_client = None
    
    print("="*60)
    print("✓ Server ready at http://localhost:8000")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    print("\n" + "="*60)
    print("👋 Shutting down server...")
    # Close MCP client
    global mcp_client
    if mcp_client:
        await mcp_client.close()
        print("✓ MCP client closed")
    print("="*60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="warning")