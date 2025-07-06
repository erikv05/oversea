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
from openai import AsyncOpenAI
from elevenlabs import generate, save, stream
import uuid
import re
import io
import time
from mcp_client import MCPClient
import queue
from typing import Optional, AsyncGenerator
import base64
import numpy as np

# Global semaphore for TTS rate limiting (max 3 concurrent requests)
TTS_SEMAPHORE = asyncio.Semaphore(3)

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
    print(f"Gemini API Key configured")
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    print("Warning: GEMINI_API_KEY not found in environment variables")
    model = None

# Configure OpenAI Whisper
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    print("OpenAI client initialized for Whisper transcription")
else:
    print("Warning: OPENAI_API_KEY not found in environment variables")
    openai_client = None

# Configure ElevenLabs API
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default Rachel voice

# Create temp directory for audio files
AUDIO_DIR = Path("temp_audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Initialize MCP client
MCP_URL = "https://mcp.zapier.com/api/mcp/s/YjFmMGM0NjItMmYwOC00Y2M3LWEyY2EtN2JjNmY3ODU5Njg3OmMyNzViMDI4LWNmYTctNDIxZi04ZDAxLTU2ODQ3ODczNTgzMQ=="
mcp_client = None

@app.get("/")
def read_root():
    return {"message": "Voice Agent API with OpenAI Whisper"}

class AudioStreamHandler:
    """Handles streaming audio to OpenAI Whisper and processing responses"""
    
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop
        self.audio_buffer = bytearray()  # Buffer for accumulating audio
        self.transcript_queue = asyncio.Queue()
        self.is_running = True
        self.current_sentence = ""
        self.processing_task = None
        self.last_speech_time = time.time()
        self.pending_transcript = ""
        self.silence_threshold = 0.7  # 700ms of silence triggers response
        self.is_listening_for_user = True  # Track if we should process user speech
        self.last_whisper_time = time.time()
        self.whisper_interval = 0.5  # Process audio every 0.5 seconds for faster response
        self.audio_lock = asyncio.Lock()
        self.min_audio_length = 4000  # Minimum 0.5 seconds of audio at 8kHz
        
    async def start(self):
        """Start the audio processing task"""
        self.processing_task = asyncio.create_task(self._process_audio_stream())
        # Start silence monitoring task
        self.silence_task = asyncio.create_task(self._monitor_silence())
        
    async def stop(self):
        """Stop audio processing"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
        if hasattr(self, 'silence_task'):
            self.silence_task.cancel()
            
    async def add_audio(self, audio_data: bytes):
        """Add audio data to the buffer"""
        if self.is_running:
            async with self.audio_lock:
                self.audio_buffer.extend(audio_data)
            # Log periodically
            if len(audio_data) > 0 and int(time.time()) % 5 == 0 and time.time() % 1 < 0.1:
                print(f"[Audio] Adding audio - listening: {self.is_listening_for_user}, buffer size: {len(self.audio_buffer)} bytes")
            
    def pause_listening(self):
        """Pause processing user speech (during agent response)"""
        print("Pausing user speech processing (but still detecting interruptions)")
        self.is_listening_for_user = False
        self.pending_transcript = ""  # Clear any pending transcript
        
    def resume_listening(self):
        """Resume processing user speech (after agent response)"""
        print("[RESUME] Starting resume_listening()")
        self.is_listening_for_user = True
        self.pending_transcript = ""  # Clear any pending transcript
        self.last_speech_time = time.time()  # Reset silence timer
        print(f"[RESUME] Set is_listening_for_user=True")
        print(f"[RESUME] Current state - is_running: {self.is_running}")
            
    async def get_transcript(self) -> Optional[str]:
        """Get the next complete sentence transcript"""
        try:
            return await asyncio.wait_for(self.transcript_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
            
    async def _process_audio_stream(self):
        """Process audio stream using OpenAI Whisper"""
        if not openai_client:
            print("OpenAI client not initialized")
            return
            
        print("[Whisper] Starting audio processing loop")
        
        while self.is_running:
            try:
                # Check if we have enough audio to process
                current_time = time.time()
                time_since_last = current_time - self.last_whisper_time
                
                async with self.audio_lock:
                    buffer_length = len(self.audio_buffer)
                
                # Process if we have enough audio and enough time has passed
                if buffer_length >= self.min_audio_length and time_since_last >= self.whisper_interval:
                    async with self.audio_lock:
                        # Extract audio for processing
                        audio_data = bytes(self.audio_buffer)
                        self.audio_buffer.clear()
                    
                    # Convert audio to WAV format for Whisper
                    wav_data = self._convert_to_wav(audio_data)
                    
                    # Send to Whisper for transcription
                    try:
                        # Create a file-like object from the WAV data
                        audio_file = io.BytesIO(wav_data)
                        audio_file.name = "audio.wav"
                        
                        # Transcribe with Whisper
                        transcript = await openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="en",
                            prompt="Real-time conversation transcription."
                        )
                        
                        if transcript.text and transcript.text.strip():
                            await self._handle_transcript(transcript.text)
                            
                        self.last_whisper_time = current_time
                        
                    except Exception as e:
                        print(f"[Whisper] Transcription error: {e}")
                
                await asyncio.sleep(0.05)  # Check every 50ms
                
            except Exception as e:
                print(f"[Whisper] Error in processing loop: {e}")
                await asyncio.sleep(0.5)
    
    def _convert_to_wav(self, audio_data: bytes) -> bytes:
        """Convert raw PCM audio to WAV format"""
        import wave
        import io
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    async def _handle_transcript(self, text: str):
        """Handle transcript from Whisper"""
        self.last_speech_time = time.time()
        
        if self.is_listening_for_user:
            # Update pending transcript
            if self.pending_transcript and not self.pending_transcript.endswith(" "):
                self.pending_transcript += " "
            self.pending_transcript += text
            
            print(f"[Whisper] Transcript (listening=True): {text}")
            print(f"[Whisper] Accumulated: {self.pending_transcript.strip()}")
            
            # Send to frontend for display
            await self.websocket.send_json({
                "type": "interim_transcript",
                "text": self.pending_transcript.strip()
            })
        else:
            # User is speaking during agent response - detect interruption
            if len(text.strip()) > 3:  # More than just noise
                print(f"[Whisper] User interruption detected: {text}")
                await self.websocket.send_json({
                    "type": "user_interruption",
                    "text": text
                })
            
    def _extract_complete_sentences(self, text: str) -> list[str]:
        """Extract complete sentences from text buffer"""
        sentences = []
        
        # Split by sentence endings
        parts = re.split(r'([.!?]\s+)', text)
        
        # Reconstruct complete sentences
        i = 0
        while i < len(parts) - 1:
            if i + 1 < len(parts) and re.match(r'[.!?]\s+', parts[i + 1]):
                sentence = parts[i] + parts[i + 1].strip()
                sentences.append(sentence)
                i += 2
            else:
                i += 1
                
        # Update buffer with remaining text
        if i < len(parts):
            self.current_sentence = parts[i]
        else:
            self.current_sentence = ""
            
        return sentences
    
    async def _monitor_silence(self):
        """Monitor for silence and trigger response when user stops speaking"""
        last_log_time = 0
        while self.is_running:
            try:
                current_time = time.time()
                time_since_speech = current_time - self.last_speech_time
                
                # Log periodically
                if current_time - last_log_time > 2.0:
                    if self.pending_transcript:
                        print(f"[Silence Monitor] Time since speech: {time_since_speech:.2f}s, pending: '{self.pending_transcript.strip()}'")
                    last_log_time = current_time
                
                # Check if we should trigger a response
                if (self.is_listening_for_user and 
                    self.pending_transcript.strip() and 
                    time_since_speech > self.silence_threshold):
                    
                    # User has stopped speaking - send the complete transcript
                    final_text = self.pending_transcript.strip()
                    print(f"[Silence Monitor] Silence detected, sending final transcript: {final_text}")
                    
                    # Clear the pending transcript
                    self.pending_transcript = ""
                    
                    # Send final transcript to frontend
                    await self.websocket.send_json({
                        "type": "user_transcript",
                        "text": final_text
                    })
                    
                    # Add to transcript queue for processing
                    await self.transcript_queue.put(final_text)
                    
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"[Silence Monitor] Error: {e}")
                await asyncio.sleep(0.5)


# Copy the rest of the original main.py file here (generate_response, stream_response, websocket endpoint, etc.)
# This includes all the LLM generation, TTS, and websocket handling code