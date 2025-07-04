from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import asyncio
from datetime import datetime
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs import generate, save
import uuid

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    print("Warning: GEMINI_API_KEY not found in environment variables")
    model = None

# Configure ElevenLabs API
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default Rachel voice

# Create temp directory for audio files
AUDIO_DIR = Path("temp_audio")
AUDIO_DIR.mkdir(exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Voice Agent API"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "message":
                user_message = data["content"]
                conversation = data.get("conversation", [])
                
                # Generate response using Gemini
                response_text = await generate_gemini_response(user_message, conversation)
                
                # Generate TTS audio using ElevenLabs
                audio_url = None
                if ELEVENLABS_API_KEY and response_text:
                    audio_url = await generate_tts_audio(response_text)
                
                # Send response back to client
                await websocket.send_json({
                    "type": "response",
                    "text": response_text,
                    "audio_url": audio_url
                })
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in websocket: {str(e)}")
        await websocket.close()

async def generate_gemini_response(user_message: str, conversation: list) -> str:
    """Generate response using Google Gemini API"""
    if not model:
        return "I'm sorry, but the AI model is not configured. Please check your API keys."
    
    try:
        # Format conversation history for Gemini
        prompt = "You are a helpful voice assistant. Keep responses concise and conversational.\n\n"
        
        # Add conversation history
        for msg in conversation[-10:]:  # Keep last 10 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        
        # Generate response
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Error generating Gemini response: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request."

async def generate_tts_audio(text: str) -> str:
    """Generate TTS audio using ElevenLabs API"""
    if not ELEVENLABS_API_KEY:
        return None
    
    try:
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = AUDIO_DIR / f"{audio_id}.mp3"
        
        # Generate audio
        audio = generate(
            api_key=ELEVENLABS_API_KEY,
            text=text,
            voice=ELEVENLABS_VOICE_ID,
            model="eleven_monolingual_v1"
        )
        
        # Save audio to file
        save(audio, str(audio_path))
        
        # Return URL path for the audio file
        return f"/audio/{audio_id}.mp3"
        
    except Exception as e:
        print(f"Error generating TTS audio: {str(e)}")
        return None

@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve audio files"""
    audio_path = AUDIO_DIR / audio_id
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/mpeg")
    return {"error": "Audio file not found"}

# Cleanup old audio files periodically
async def cleanup_audio_files():
    """Remove audio files older than 1 hour"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        try:
            for audio_file in AUDIO_DIR.glob("*.mp3"):
                if (datetime.now() - datetime.fromtimestamp(audio_file.stat().st_mtime)).seconds > 3600:
                    audio_file.unlink()
        except Exception as e:
            print(f"Error cleaning up audio files: {str(e)}")

@app.on_event("startup")
async def startup_event():
    # Start cleanup task
    asyncio.create_task(cleanup_audio_files())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)