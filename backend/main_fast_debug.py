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
from elevenlabs import generate, save, stream, Voice, VoiceSettings
import uuid
import re
import io
import time
from mcp_client import MCPClient
import queue
from typing import Optional, AsyncGenerator
import wave

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
    print(f"✓ Gemini API Key configured")
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    print("✗ Warning: GEMINI_API_KEY not found in environment variables")
    model = None

# Configure OpenAI Whisper
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")  # Default to stable model
if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    print(f"✓ OpenAI client initialized (model: {WHISPER_MODEL})")
else:
    print("✗ Warning: OPENAI_API_KEY not found")
    openai_client = None

# Configure ElevenLabs API
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default Rachel voice
if ELEVENLABS_API_KEY:
    print(f"✓ ElevenLabs configured (voice: {ELEVENLABS_VOICE_ID})")
else:
    print("✗ Warning: ELEVENLABS_API_KEY not found")

# Create temp directory for audio files
AUDIO_DIR = Path("temp_audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Initialize MCP client
MCP_URL = "https://mcp.zapier.com/api/mcp/s/YjFmMGM0NjItMmYwOC00Y2M3LWEyY2EtN2JjNmY3ODU5Njg3OmMyNzViMDI4LWNmYTctNDIxZi04ZDAxLTU2ODQ3ODczNTgzMQ=="
mcp_client = None

def timestamp():
    """Return a formatted timestamp for logging"""
    return f"[{time.time():.3f}]"

@app.get("/")
def read_root():
    return {"message": "Voice Agent API - Fast Response Version"}

class AudioStreamHandler:
    """Handles streaming audio with aggressive Voice Activity Detection for speed"""
    
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop
        self.is_running = True
        self.is_listening_for_user = True
        
        # Voice Activity Detection parameters
        self.speech_buffer = bytearray()  # Buffer for current speech segment
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        
        # Pre-speech circular buffer (200ms = 1600 samples at 8kHz, 16-bit = 3200 bytes)
        self.pre_speech_buffer_size = 3200  # 200ms of audio
        self.pre_speech_buffer = bytearray()
        
        # Aggressive thresholds for fast response
        self.energy_threshold = 200  # Lower threshold for better sensitivity
        self.speech_start_frames = 2  # 20ms to start
        self.speech_end_frames = 30   # 300ms of silence (more aggressive)
        self.frame_size = 160  # 10ms frames at 8kHz
        
        # Speculative processing
        self.speculative_task = None
        self.last_speculative_time = 0
        self.min_speech_duration = 3200  # 400ms minimum speech
        
        # Transcript handling
        self.transcript_queue = asyncio.Queue()
        self.processing_task = None
        
        # Performance tracking
        self.speech_start_time = None
        
    async def start(self):
        """Start the audio processing task"""
        self.processing_task = asyncio.create_task(self._process_audio_stream())
        
    async def stop(self):
        """Stop audio processing"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
        if self.speculative_task and not self.speculative_task.done():
            self.speculative_task.cancel()
            
    async def add_audio(self, audio_data: bytes):
        """Process incoming audio data with VAD"""
        if not self.is_running:
            return
            
        # Process audio in frames for VAD
        for i in range(0, len(audio_data), self.frame_size):
            frame = audio_data[i:i + self.frame_size]
            if len(frame) < self.frame_size:
                break  # Skip incomplete frames
                
            # Always add to pre-speech buffer (circular buffer)
            self._add_to_pre_speech_buffer(frame)
                
            # Calculate frame energy
            frame_energy = self._calculate_frame_energy(frame)
            
            # Voice Activity Detection logic
            if frame_energy > self.energy_threshold:
                # Speech detected
                self.speech_counter += 1
                self.silence_counter = 0
                
                if not self.is_speaking and self.speech_counter >= self.speech_start_frames:
                    # Start of speech detected
                    self.is_speaking = True
                    self.speech_start_time = time.time()
                    print(f"{timestamp()} 🎤 Speech started (energy: {frame_energy:.0f})")
                    
                    # Add pre-speech buffer to capture beginning of speech
                    self.speech_buffer.extend(self.pre_speech_buffer)
                    
                    await self.websocket.send_json({
                        "type": "speech_start",
                        "timestamp": time.time()
                    })
                
                if self.is_speaking:
                    # Add frame to speech buffer
                    self.speech_buffer.extend(frame)
            else:
                # Silence detected
                self.silence_counter += 1
                self.speech_counter = 0
                
                if self.is_speaking:
                    # Continue adding to buffer during short pauses
                    self.speech_buffer.extend(frame)
                    
                    # Start speculative processing after just 100ms of silence
                    if self.silence_counter == 10 and len(self.speech_buffer) > self.min_speech_duration:
                        # Cancel any existing speculative task
                        if self.speculative_task and not self.speculative_task.done():
                            self.speculative_task.cancel()
                        
                        # Start speculative transcription
                        print(f"{timestamp()} 🔮 Starting speculative processing (100ms silence)")
                        self.speculative_task = asyncio.create_task(
                            self._speculative_process(bytes(self.speech_buffer))
                        )
                    
                    # Final end of speech after 300ms
                    if self.silence_counter >= self.speech_end_frames:
                        # End of speech detected
                        self.is_speaking = False
                        speech_duration = time.time() - self.speech_start_time
                        print(f"{timestamp()} 🛑 Speech ended (duration: {speech_duration:.2f}s)")
                        
                        # If we have a speculative task running, it's now the real deal
                        if self.speculative_task and not self.speculative_task.done():
                            print(f"{timestamp()} ✓ Using speculative result")
                            # The speculative task will handle everything
                        else:
                            # Process normally if no speculative task
                            if len(self.speech_buffer) > self.min_speech_duration:
                                await self._process_speech_segment(bytes(self.speech_buffer))
                        
                        # Clear the buffer
                        self.speech_buffer.clear()
                        
                        await self.websocket.send_json({
                            "type": "speech_end",
                            "timestamp": time.time()
                        })
    
    def _add_to_pre_speech_buffer(self, frame: bytes):
        """Add frame to circular pre-speech buffer"""
        self.pre_speech_buffer.extend(frame)
        # Keep only the last 200ms of audio
        if len(self.pre_speech_buffer) > self.pre_speech_buffer_size:
            # Remove oldest data
            self.pre_speech_buffer = self.pre_speech_buffer[-self.pre_speech_buffer_size:]
    
    def _calculate_frame_energy(self, frame: bytes) -> float:
        """Calculate the energy level of an audio frame"""
        # Convert bytes to 16-bit integers
        energy = 0
        num_samples = 0
        
        for i in range(0, len(frame) - 1, 2):
            value = int.from_bytes(frame[i:i+2], byteorder='little', signed=True)
            energy += abs(value)
            num_samples += 1
        
        return energy / num_samples if num_samples > 0 else 0
    
    async def _speculative_process(self, audio_data: bytes):
        """Speculatively process audio before we're 100% sure speech has ended"""
        speculative_start = time.time()
        try:
            print(f"{timestamp()} 🔮 [1/5] Speculative: Creating Whisper task")
            # Start Whisper transcription immediately
            transcript_task = asyncio.create_task(self._transcribe_audio(audio_data))
            
            # Wait a bit to see if more speech comes
            print(f"{timestamp()} 🔮 [2/5] Speculative: Waiting 100ms to confirm silence")
            await asyncio.sleep(0.1)  # 100ms more
            
            # If we're still speaking, this was premature - cancel
            if self.is_speaking:
                print(f"{timestamp()} 🔮 Speculative cancelled - user still speaking")
                transcript_task.cancel()
                return
            
            print(f"{timestamp()} 🔮 [3/5] Speculative: Confirmed silence, waiting for transcript")
            # Otherwise, get the transcript and process
            transcript_text = await transcript_task
            
            if transcript_text:
                transcript_ready_time = time.time() - speculative_start
                print(f"{timestamp()} 🔮 [4/5] Speculative success: '{transcript_text}' (total: {transcript_ready_time:.3f}s)")
                
                # Send transcript to frontend
                print(f"{timestamp()} 🔮 [5/5] Speculative: Sending to frontend")
                await self.websocket.send_json({
                    "type": "user_transcript",
                    "text": transcript_text,
                    "timestamp": time.time()
                })
                
                # Add to queue for processing
                await self.transcript_queue.put(transcript_text)
                
        except asyncio.CancelledError:
            print(f"{timestamp()} 🔮 Speculative task cancelled")
        except Exception as e:
            print(f"{timestamp()} ❌ Speculative error: {e}")
    
    async def _transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio with Whisper"""
        try:
            transcribe_start = time.time()
            print(f"{timestamp()} 🎯 [Whisper 1/6] Starting transcription pipeline")
            
            # Convert to WAV
            print(f"{timestamp()} 🎯 [Whisper 2/6] Converting PCM to WAV")
            wav_convert_start = time.time()
            wav_data = self._convert_to_wav(audio_data)
            wav_convert_time = time.time() - wav_convert_start
            print(f"{timestamp()} 🎯 [Whisper 3/6] WAV conversion done ({wav_convert_time:.3f}s)")
            
            # Create file-like object
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            audio_duration = len(audio_data)/16000
            print(f"{timestamp()} 🎯 [Whisper 4/6] Sending {audio_duration:.1f}s audio to OpenAI API")
            api_start = time.time()
            
            # Transcribe with Whisper
            transcript = await openai_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                prompt="Accurate transcription of spoken words."
            )
            
            api_time = time.time() - api_start
            print(f"{timestamp()} 🎯 [Whisper 5/6] OpenAI API responded ({api_time:.3f}s)")
            
            transcript_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            
            # Check for hallucinations
            hallucination_patterns = [
                "www.", ".com", ".gov", ".org",
                "transcription by", "translation by", 
                "for more information visit",
                "thank you for watching"
            ]
            
            is_hallucination = any(pattern.lower() in transcript_text.lower() for pattern in hallucination_patterns)
            
            if is_hallucination:
                print(f"{timestamp()} ⚠️  Whisper: Rejected hallucination")
                return None
            
            total_time = time.time() - transcribe_start
            print(f"{timestamp()} 🎯 [Whisper 6/6] Complete! Total: {total_time:.3f}s (prep: {wav_convert_time:.3f}s, API: {api_time:.3f}s)")
            
            return transcript_text.strip()
            
        except Exception as e:
            print(f"{timestamp()} ❌ Whisper error: {e}")
            return None
    
    async def _process_speech_segment(self, audio_data: bytes):
        """Process a complete speech segment with Whisper"""
        if not self.is_listening_for_user:
            # User is interrupting - just notify
            print(f"{timestamp()} 🔊 User interruption during agent response")
            await self.websocket.send_json({
                "type": "user_interruption",
                "text": "[User speaking]",
                "timestamp": time.time()
            })
            return
        
        transcript_text = await self._transcribe_audio(audio_data)
        
        if transcript_text:
            # Send transcript to frontend
            await self.websocket.send_json({
                "type": "user_transcript",
                "text": transcript_text,
                "timestamp": time.time()
            })
            
            # Add to queue for processing
            await self.transcript_queue.put(transcript_text)
    
    def _convert_to_wav(self, audio_data: bytes) -> bytes:
        """Convert raw PCM audio to WAV format"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    def pause_listening(self):
        """Pause processing user speech (during agent response)"""
        print(f"{timestamp()} ⏸️  Pausing user speech processing")
        self.is_listening_for_user = False
        
    def resume_listening(self):
        """Resume processing user speech (after agent response)"""
        print(f"{timestamp()} ▶️  Resuming user speech processing")
        self.is_listening_for_user = True
        # Clear any buffered audio
        self.speech_buffer.clear()
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        
    async def get_transcript(self) -> Optional[str]:
        """Get the next complete transcript"""
        try:
            return await asyncio.wait_for(self.transcript_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    async def _process_audio_stream(self):
        """Dummy task for compatibility"""
        # All processing now happens in add_audio with VAD
        while self.is_running:
            await asyncio.sleep(1)


async def generate_gemini_response_stream(user_message: str, conversation: list):
    """Generate streaming response using Google Gemini API"""
    if not model:
        yield "I'm sorry, but the AI model is not configured. Please check your API keys."
        return
    
    try:
        start_time = time.time()
        
        # Simplified prompt for speed
        prompt = "You are a conversational voice assistant. Be concise and natural.\n\n"
        
        # Minimal conversation history (last 4 messages for speed)
        for msg in conversation[-4:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        
        prompt += f"User: {user_message}\nAssistant: "
        
        print(f"{timestamp()} 🤖 LLM: Generating response for '{user_message}'")
        
        # Generate streaming response
        response = model.generate_content(prompt, stream=True)
        
        first_token_time = None
        buffer = ""
        char_count = 0
        
        for chunk in response:
            if chunk.text:
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                    print(f"{timestamp()} ✓ LLM: First token in {first_token_time:.2f}s")
                
                buffer += chunk.text
                char_count += len(chunk.text)
                
                # Yield more aggressively for faster response
                yield chunk.text
        
        total_time = time.time() - start_time
        print(f"{timestamp()} ✓ LLM: Complete ({char_count} chars in {total_time:.2f}s)")
                
    except Exception as e:
        print(f"{timestamp()} ❌ LLM error: {str(e)}")
        yield "I'm sorry, I encountered an error while processing your request."

async def generate_tts_audio_fast(text: str) -> str:
    """Generate TTS audio using ElevenLabs API with optimizations"""
    if not ELEVENLABS_API_KEY:
        return None
    
    try:
        start_time = time.time()
        
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = AUDIO_DIR / f"{audio_id}.mp3"
        
        print(f"{timestamp()} 🔊 TTS: Generating audio for '{text[:50]}...'")
        
        # Use the fastest settings
        voice_settings = VoiceSettings(
            stability=0.5,  # Lower for faster generation
            similarity_boost=0.75
        )
        
        # Run the blocking ElevenLabs API call in a thread pool
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,  # Use default thread pool
            lambda: generate(
                api_key=ELEVENLABS_API_KEY,
                text=text,
                voice=Voice(
                    voice_id=ELEVENLABS_VOICE_ID,
                    settings=voice_settings
                ),
                model="eleven_turbo_v2"  # Fastest model
            )
        )
        
        # Save audio to file
        await loop.run_in_executor(None, save, audio, str(audio_path))
        
        generation_time = time.time() - start_time
        print(f"{timestamp()} ✓ TTS: Complete in {generation_time:.2f}s")
        
        # Return URL path for the audio file
        return f"/audio/{audio_id}"
        
    except Exception as e:
        print(f"{timestamp()} ❌ TTS error: {str(e)}")
        return None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"\n{timestamp()} 🔌 WebSocket connection from {websocket.client}")
    await websocket.accept()
    print(f"{timestamp()} ✓ WebSocket connected")
    
    # Initialize audio stream handler with current event loop
    loop = asyncio.get_event_loop()
    audio_handler = AudioStreamHandler(websocket, loop)
    await audio_handler.start()
    
    # Track active generation tasks
    active_tasks = set()
    current_generation_id = 0
    
    # Track conversation
    conversation = []
    
    try:
        while True:
            # Receive message from client (could be JSON or binary audio)
            message = await websocket.receive()
            
            if "text" in message:
                # JSON message
                data = json.loads(message["text"])
                
                if data.get("type") == "audio_config":
                    # Client is configuring audio settings
                    print(f"{timestamp()} ⚙️  Audio config received")
                    
                elif data.get("type") == "interrupt":
                    # Cancel all active tasks
                    print(f"{timestamp()} 🛑 Interruption - cancelling {len(active_tasks)} tasks")
                    for task in active_tasks:
                        if not task.done():
                            task.cancel()
                    active_tasks.clear()
                    current_generation_id += 1  # Increment ID to invalidate old responses
                    
            elif "bytes" in message:
                # Binary audio data
                audio_data = message["bytes"]
                await audio_handler.add_audio(audio_data)
                
                # Check for complete transcripts
                transcript = await audio_handler.get_transcript()
                if transcript:
                    response_pipeline_start = time.time()
                    # Calculate delay from speech end
                    if audio_handler.speech_start_time:
                        speech_end_time = response_pipeline_start  # Approximate
                        transcript_delay = response_pipeline_start - audio_handler.speech_start_time
                        print(f"\n{timestamp()} 📝 Transcript: '{transcript}' (received {transcript_delay:.2f}s after speech start)")
                    else:
                        print(f"\n{timestamp()} 📝 Transcript: '{transcript}'")
                    print(f"{timestamp()} ⏱️  Starting response pipeline...")
                    
                    # Pause listening while we process the response
                    audio_handler.pause_listening()
                    
                    # Don't add to conversation here - frontend handles it
                    # conversation.append({"role": "user", "content": transcript})
                    
                    # Start streaming response
                    await websocket.send_json({
                        "type": "stream_start",
                        "timestamp": time.time()
                    })
                    
                    # Increment generation ID for this response
                    current_generation_id += 1
                    generation_id = current_generation_id
                    
                    # Stream response with aggressive TTS generation
                    async def stream_response(gen_id: int):
                        if gen_id != current_generation_id:
                            return
                        
                        try:
                            full_response = ""
                            first_sentence = ""
                            first_tts_task = None
                            
                            # Track timing
                            llm_start = time.time()
                            
                            async for text_chunk in generate_gemini_response_stream(transcript, conversation):
                                if gen_id != current_generation_id:
                                    raise asyncio.CancelledError()
                                
                                full_response += text_chunk
                                
                                # Send text chunk immediately
                                await websocket.send_json({
                                    "type": "text_chunk",
                                    "text": text_chunk,
                                    "timestamp": time.time()
                                })
                                
                                # Generate TTS for first sentence ASAP
                                if not first_tts_task and re.search(r'[.!?]', full_response):
                                    # Extract first sentence
                                    match = re.search(r'^(.*?[.!?])\s*', full_response)
                                    if match:
                                        first_sentence = match.group(1)
                                        print(f"{timestamp()} 🎯 First sentence ready, starting TTS")
                                        first_tts_task = asyncio.create_task(
                                            generate_tts_audio_fast(first_sentence)
                                        )
                                        active_tasks.add(first_tts_task)
                                        first_tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                            
                            # Wait for first TTS if we have one
                            if first_tts_task:
                                audio_url = await first_tts_task
                                if audio_url:
                                    first_audio_time = time.time() - response_pipeline_start
                                    print(f"{timestamp()} 🎉 First audio ready in {first_audio_time:.2f}s from user stop")
                                    
                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "audio_url": audio_url,
                                        "text": first_sentence,
                                        "timestamp": time.time()
                                    })
                            
                            # Generate TTS for remaining text if any
                            remaining_text = full_response[len(first_sentence):].strip()
                            if remaining_text and remaining_text not in ["", "."]:
                                print(f"{timestamp()} 🔊 TTS: Generating remaining audio")
                                remaining_audio_url = await generate_tts_audio_fast(remaining_text)
                                if remaining_audio_url:
                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "audio_url": remaining_audio_url,
                                        "text": remaining_text,
                                        "timestamp": time.time()
                                    })
                            
                            # Add complete response to conversation
                            conversation.append({"role": "assistant", "content": full_response})
                            
                            # Send stream complete
                            await websocket.send_json({
                                "type": "stream_complete",
                                "full_text": full_response,
                                "timestamp": time.time()
                            })
                            
                            total_time = time.time() - response_pipeline_start
                            print(f"{timestamp()} ✅ Response pipeline complete in {total_time:.2f}s")
                            
                            # Calculate actual user-perceived delay
                            if audio_handler.speech_start_time:
                                user_perceived_delay = time.time() - audio_handler.speech_start_time
                                speech_to_audio_delay = first_audio_time
                                print(f"{timestamp()} 📊 Timing Breakdown:")
                                print(f"    • Speech start → Speech end: {(response_pipeline_start - audio_handler.speech_start_time):.2f}s")
                                print(f"    • Speech end → Transcript: ~0.2s (speculative)")  
                                print(f"    • Transcript → First token: {(llm_start - response_pipeline_start):.2f}s")
                                print(f"    • First token → First audio: {(first_audio_time - (llm_start - response_pipeline_start)):.2f}s")
                                print(f"    • Speech end → First audio: {first_audio_time:.2f}s")
                                print(f"    • 🎯 Total user-perceived delay: {user_perceived_delay:.2f}s\n")
                            else:
                                print(f"{timestamp()} 📊 Standard Breakdown:")
                                print(f"    • Speech end → Transcript: ~0.2s (speculative)")
                                print(f"    • Transcript → First token: {(llm_start - response_pipeline_start):.2f}s")
                                print(f"    • First token → First audio: {(first_audio_time - (llm_start - response_pipeline_start)):.2f}s")
                                print(f"    • Total: {total_time:.2f}s\n")
                            
                            # Resume listening for user input
                            audio_handler.resume_listening()
                            
                        except asyncio.CancelledError:
                            print(f"{timestamp()} ❌ Stream cancelled (interruption)")
                            await websocket.send_json({
                                "type": "stream_complete",
                                "full_text": full_response,
                                "interrupted": True,
                                "timestamp": time.time()
                            })
                            audio_handler.resume_listening()
                            raise
                    
                    # Run the streaming in a task
                    stream_task = asyncio.create_task(stream_response(generation_id))
                    active_tasks.add(stream_task)
                    stream_task.add_done_callback(lambda t: active_tasks.discard(t))
                    
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        print(f"{timestamp()} ❌ Stream error: {e}")
                        import traceback
                        traceback.print_exc()
                    
    except WebSocketDisconnect:
        print(f"{timestamp()} 🔌 Client disconnected")
        await audio_handler.stop()
    except Exception as e:
        print(f"{timestamp()} ❌ WebSocket error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await audio_handler.stop()

@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve audio files"""
    # Add .mp3 extension if not present
    if not audio_id.endswith('.mp3'):
        audio_id = f"{audio_id}.mp3"
    
    audio_path = AUDIO_DIR / audio_id
    
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/mpeg")
    else:
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
    uvicorn.run("main_fast_debug:app", host="0.0.0.0", port=8000, reload=True, log_level="warning")