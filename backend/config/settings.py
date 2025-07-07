"""Configuration settings for the Voice Agent API"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default Rachel voice
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")  # Default to stable model
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# MCP Configuration
MCP_URL = "https://mcp.zapier.com/api/mcp/s/YjFmMGM0NjItMmYwOC00Y2M3LWEyY2EtN2JjNmY3ODU5Njg3OmMyNzViMDI4LWNmYTctNDIxZi04ZDAxLTU2ODQ3ODczNTgzMQ=="

# Directory Configuration
AUDIO_DIR = Path("/app/backend/temp_audio")
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# Server Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
# In production, this will be set to the Cloud Run service URL

# Voice Activity Detection Parameters
VAD_CONFIG = {
    "min_speech_duration": 1600,  # 200ms (reduced from 400ms for faster interruptions)
    "pre_speech_buffer_size": 1600,  # 100ms (reduced from 200ms)
}

# Model Configuration
GEMINI_MODEL = "gemini-2.0-flash-exp"
ELEVENLABS_MODEL = "eleven_turbo_v2"