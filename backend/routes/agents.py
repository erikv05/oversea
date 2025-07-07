"""Agent management routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/agents", tags=["agents"])

# In-memory storage for agents
agents_db: Dict[str, dict] = {}

# Agent model
class AgentBase(BaseModel):
    name: str
    voice: str = "Vincent"
    speed: str = "1.0x"
    greeting: str = ""
    system_prompt: str = ""
    behavior: str = "professional"
    llm_model: str = "GPT 4o"
    custom_knowledge: str = ""
    guardrails_enabled: bool = False
    current_date_enabled: bool = True
    caller_info_enabled: bool = True
    timezone: str = "(GMT-08:00) Pacific Time (US & Canada)"

class AgentCreate(AgentBase):
    pass

class AgentUpdate(AgentBase):
    name: Optional[str] = None
    voice: Optional[str] = None
    speed: Optional[str] = None
    greeting: Optional[str] = None
    system_prompt: Optional[str] = None
    behavior: Optional[str] = None
    llm_model: Optional[str] = None
    custom_knowledge: Optional[str] = None
    guardrails_enabled: Optional[bool] = None
    current_date_enabled: Optional[bool] = None
    caller_info_enabled: Optional[bool] = None
    timezone: Optional[str] = None

class Agent(AgentBase):
    id: str
    agent_id: str
    created_at: datetime
    updated_at: datetime
    conversations: int = 0
    minutes_spoken: float = 0.0
    knowledge_resources: int = 0

@router.get("/", response_model=List[Agent])
async def get_agents():
    """Get all agents"""
    return list(agents_db.values())

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_db[agent_id]

@router.post("/", response_model=Agent)
async def create_agent(agent: AgentCreate):
    """Create a new agent"""
    # Generate unique IDs
    agent_id = str(uuid.uuid4())
    agent_display_id = f"{agent.name.replace(' ', '-')}-{agent_id[:8]}"
    
    # Create agent object
    new_agent = Agent(
        **agent.dict(),
        id=agent_id,
        agent_id=agent_display_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Store in memory
    agents_db[agent_id] = new_agent.dict()
    
    return new_agent

@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_update: AgentUpdate):
    """Update an existing agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get existing agent
    existing_agent = agents_db[agent_id]
    
    # Update only provided fields
    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        existing_agent[field] = value
    
    # Update timestamp
    existing_agent["updated_at"] = datetime.now()
    
    # If name changed, update agent_id
    if "name" in update_data:
        existing_agent["agent_id"] = f"{update_data['name'].replace(' ', '-')}-{agent_id[:8]}"
    
    return existing_agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    del agents_db[agent_id]
    return {"message": "Agent deleted successfully"}

@router.post("/{agent_id}/conversation")
async def update_agent_stats(agent_id: str, duration_seconds: float):
    """Update agent conversation statistics"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[agent_id]
    agent["conversations"] += 1
    agent["minutes_spoken"] += duration_seconds / 60
    agent["updated_at"] = datetime.now()
    
    return {"message": "Stats updated successfully"}

# Initialize with sample agents (matching the frontend)
def init_sample_agents():
    """Initialize with sample agents for testing"""
    sample_agents = [
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
            "timezone": "(GMT-08:00) Pacific Time (US & Canada)"
        },
        {
            "name": "Untitled Agent",
            "voice": "Vincent",
            "speed": "1.0x", 
            "greeting": "Hi there! How can I assist you?",
            "system_prompt": "You are a friendly conversational assistant.",
            "behavior": "chatty",
            "llm_model": "GPT 4o",
            "custom_knowledge": "",
            "guardrails_enabled": False,
            "current_date_enabled": True,
            "caller_info_enabled": True,
            "timezone": "(GMT-08:00) Pacific Time (US & Canada)"
        }
    ]
    
    for agent_data in sample_agents:
        agent_create = AgentCreate(**agent_data)
        agent_id = str(uuid.uuid4())
        agent_display_id = f"{agent_data['name'].replace(' ', '-')}-{agent_id[:8]}"
        
        new_agent = Agent(
            **agent_create.dict(),
            id=agent_id,
            agent_id=agent_display_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            conversations=3 if agent_data["name"] == "Bozidar" else 2,
            minutes_spoken=1.1 if agent_data["name"] == "Bozidar" else 0
        )
        
        agents_db[agent_id] = new_agent.dict()

# Initialize sample agents on import
init_sample_agents()