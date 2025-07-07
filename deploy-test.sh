#!/bin/bash
# Test deployment without requiring API keys

set -e

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Building test deployment for project: $PROJECT_ID"

# Create a temporary test backend
cat > backend/test_main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample agents
agents = {
    "1": {
        "id": "1",
        "agent_id": "agent-1",
        "name": "Bozidar",
        "voice": "Vincent",
        "speed": "1.0x",
        "greeting": "Hello! I'm Bozidar. How can I help you today?",
        "system_prompt": "You are Bozidar, a helpful assistant.",
        "behavior": "professional",
        "llm_model": "GPT 4o",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "conversations": 3,
        "minutes_spoken": 1.1,
        "status": "active"
    }
}

@app.get("/")
def root():
    return {"message": "Voice Agent API", "version": "2.0"}

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "backend": "test",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/agents/")
def get_agents():
    return list(agents.values())

@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: str):
    return agents.get(agent_id, {"error": "Agent not found"})

@app.post("/api/agents/")
def create_agent(data: dict):
    agent_id = str(uuid.uuid4())
    agent = {
        "id": agent_id,
        "agent_id": f"agent-{agent_id[:8]}",
        **data,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "conversations": 0,
        "minutes_spoken": 0.0,
        "status": "active"
    }
    agents[agent_id] = agent
    return agent

# Stub websocket
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected"})
    await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Update supervisord to use test backend
sed -i.bak 's/main:app/test_main:app/g' cloudrun/supervisord.conf

# Deploy
gcloud builds submit --config=cloudbuild-simple.yaml \
  --substitutions=_GEMINI_API_KEY="test",_DEEPGRAM_API_KEY="test",_ELEVENLABS_API_KEY="test",_ELEVENLABS_VOICE_ID="test"

# Restore original supervisord
mv cloudrun/supervisord.conf.bak cloudrun/supervisord.conf

# Remove test file
rm backend/test_main.py

# Get service URL and test
SERVICE_URL=$(gcloud run services describe voice-agent --region us-central1 --format 'value(status.url)')
echo ""
echo "Testing deployment..."
echo "Service URL: $SERVICE_URL"
echo ""

# Test health endpoint
echo "Testing /api/health:"
curl -s "$SERVICE_URL/api/health" | python3 -m json.tool

echo ""
echo "Testing /api/agents/:"
curl -s "$SERVICE_URL/api/agents/" | python3 -m json.tool | head -20