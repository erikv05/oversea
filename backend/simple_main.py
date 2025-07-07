"""Minimal FastAPI app for debugging"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

@app.get("/api/test")
def test():
    return {"test": "working"}

@app.get("/api/agents/")
def get_agents():
    return []

@app.post("/api/agents/")
def create_agent(data: dict):
    return {"id": "123", "message": "Agent created"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)