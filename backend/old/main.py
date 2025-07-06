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
    print(f"Gemini API Key configured")
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    print("Warning: GEMINI_API_KEY not found in environment variables")
    model = None

# Configure OpenAI Whisper
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")  # Default to stable model
if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    print(f"OpenAI client initialized for Whisper transcription using model: {WHISPER_MODEL}")
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
    return {"message": "Voice Agent API with OpenAI Whisper and VAD"}

class AudioStreamHandler:
    """Handles streaming audio with Voice Activity Detection (VAD)"""
    
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
        
        # Thresholds for VAD
        self.energy_threshold = 250  # Energy level to detect speech (lowered for better sensitivity)
        self.speech_start_frames = 2  # Frames of speech to start recording (20ms)
        self.speech_end_frames = 100  # Frames of silence to end recording (1 full second)
        self.frame_size = 160  # 10ms frames at 8kHz for more responsive detection
        
        # Transcript handling
        self.transcript_queue = asyncio.Queue()
        
        # Processing task
        self.processing_task = None
        
    async def start(self):
        """Start the audio processing task"""
        self.processing_task = asyncio.create_task(self._process_audio_stream())
        
    async def stop(self):
        """Stop audio processing"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            
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
                    print(f"[VAD] Speech started (energy: {frame_energy:.1f})")
                    
                    # Add pre-speech buffer to capture beginning of speech
                    self.speech_buffer.extend(self.pre_speech_buffer)
                    print(f"[VAD] Added {len(self.pre_speech_buffer)} bytes of pre-speech audio")
                    
                    await self.websocket.send_json({
                        "type": "speech_start"
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
                    
                    if self.silence_counter >= self.speech_end_frames:
                        # End of speech detected
                        self.is_speaking = False
                        print(f"[VAD] Speech ended after {self.silence_counter * 10}ms of silence (buffer size: {len(self.speech_buffer)} bytes)")
                        
                        # Process the complete speech segment
                        if len(self.speech_buffer) > 8000:  # At least 1 second of audio
                            await self._process_speech_segment(bytes(self.speech_buffer))
                        else:
                            print(f"[VAD] Speech segment too short ({len(self.speech_buffer)} bytes), discarding")
                        
                        # Clear the buffer
                        self.speech_buffer.clear()
                        
                        await self.websocket.send_json({
                            "type": "speech_end"
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
    
    async def _process_speech_segment(self, audio_data: bytes):
        """Process a complete speech segment with Whisper"""
        if not self.is_listening_for_user:
            # User is interrupting - just notify
            print("[VAD] User interruption detected during agent response")
            await self.websocket.send_json({
                "type": "user_interruption",
                "text": "[User speaking]"
            })
            return
            
        try:
            # Convert to WAV
            wav_data = self._convert_to_wav(audio_data)
            
            # Create file-like object
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            print(f"[Whisper] Sending {len(audio_data)/16000:.1f}s of speech to Whisper")
            
            # Transcribe with Whisper
            transcript = await openai_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                prompt="Accurate transcription of spoken words."
            )
            
            transcript_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            
            print(f"[Whisper] Transcription result: '{transcript_text}'")
            
            # Check for hallucinations
            hallucination_patterns = [
                "www.", ".com", ".gov", ".org",
                "transcription by", "translation by", 
                "for more information visit",
                "thank you for watching"
            ]
            
            is_hallucination = any(pattern.lower() in transcript_text.lower() for pattern in hallucination_patterns)
            
            if is_hallucination:
                print(f"[Whisper] Rejected hallucination: '{transcript_text}'")
                return
            
            # Send transcript to frontend
            if transcript_text.strip():
                await self.websocket.send_json({
                    "type": "user_transcript",
                    "text": transcript_text.strip()
                })
                
                # Add to queue for processing
                await self.transcript_queue.put(transcript_text.strip())
                
        except Exception as e:
            print(f"[Whisper] Error transcribing speech: {e}")
    
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
        print("[VAD] Pausing user speech processing")
        self.is_listening_for_user = False
        
    def resume_listening(self):
        """Resume processing user speech (after agent response)"""
        print("[VAD] Resuming user speech processing")
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
        # Format conversation history for Gemini
        prompt = "You are a helpful voice assistant with access to external tools. Keep responses concise and conversational. Start your response immediately without any preamble.\n\n"
        prompt += "Only use tools when the user explicitly asks for an action that requires them. For example, only create calendar events when the user asks you to schedule, add, or create a meeting or appointment.\n"
        prompt += f"Today's date is {datetime.now().strftime('%Y-%m-%d')}.\n\n"
        
        # Add available tools if MCP is connected
        if mcp_client and mcp_client.tools:
            prompt += "Available tools:\n"
            prompt += mcp_client.get_tools_description()
            prompt += "\n\nTo use a tool, respond with a JSON block in this format:\n"
            prompt += '```tool\n{"tool": "tool_name", "arguments": {"param1": "value1"}}\n```\n'
            prompt += "After using a tool, continue with your response based on the result.\n"
            prompt += "IMPORTANT: All tools require an 'instructions' parameter that describes what to do.\n"
            prompt += "For calendar events, use google_calendar_quick_add_event with both 'text' and 'instructions' parameters.\n"
            prompt += "Example: ```tool\n{\"tool\": \"google_calendar_quick_add_event\", \"arguments\": {\"text\": \"Meeting tomorrow at 8am\", \"instructions\": \"Create a meeting tomorrow at 8am\"}}\n```\n\n"
        
        # Add conversation history
        for msg in conversation[-10:]:  # Keep last 10 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        
        # Add current user message
        prompt += f"User: {user_message}\n"
        prompt += "Assistant: "
        
        print(f"Prompt:\n{prompt[-500:]}")  # Log last 500 chars of prompt
        
        # Generate streaming response
        response = model.generate_content(prompt, stream=True)
        
        buffer = ""
        for chunk in response:
            if chunk.text:
                buffer += chunk.text
                
                # Check for tool calls in the buffer
                tool_pattern = r'```tool\n(.*?)\n```'
                match = re.search(tool_pattern, buffer, re.DOTALL)
                
                if match:
                    # Extract and execute tool call
                    try:
                        tool_json = match.group(1).strip()
                        print(f"Found tool call JSON: {tool_json}")
                        tool_call = json.loads(tool_json)
                        tool_name = tool_call.get("tool")
                        arguments = tool_call.get("arguments", {})
                        
                        print(f"Executing tool: {tool_name} with arguments: {arguments}")
                        
                        # Execute tool call
                        if mcp_client:
                            # Add instructions parameter if not present (required by Zapier MCP)
                            if "instructions" not in arguments:
                                # Generate instructions based on the tool and arguments
                                if tool_name == "google_calendar_create_detailed_event":
                                    summary = arguments.get("summary", "Event")
                                    start = arguments.get("start__dateTime", "")
                                    end = arguments.get("end__dateTime", "")
                                    arguments["instructions"] = f"Create an event called '{summary}' from {start} to {end}"
                                elif tool_name == "google_calendar_quick_add_event":
                                    text = arguments.get("text", "")
                                    arguments["instructions"] = f"Create an event: {text}"
                                else:
                                    arguments["instructions"] = f"Execute {tool_name} with provided arguments"
                            
                            # Yield the text before the tool call
                            pre_tool_text = buffer[:match.start()]
                            if pre_tool_text:
                                yield pre_tool_text
                            else:
                                # If no text before tool call, announce what we're doing
                                if "calendar" in tool_name and "create" in tool_name.lower():
                                    yield "I'll create that calendar event for you. "
                                elif "calendar" in tool_name and "find" in tool_name.lower():
                                    yield "Let me check your calendar. "
                                else:
                                    yield f"Let me {tool_name.replace('_', ' ')} for you. "
                            try:
                                # Add a timeout to the MCP call
                                result = await asyncio.wait_for(
                                    mcp_client.call_tool(tool_name, arguments),
                                    timeout=30.0  # 30 second timeout
                                )
                                print(f"MCP call completed")
                                print(f"MCP call result: {result}")
                            except asyncio.TimeoutError:
                                print(f"MCP call timed out after 30 seconds")
                                result = {"error": "The operation timed out. The calendar event may still be created in the background."}
                            
                            # Yield tool result in a user-friendly way
                            if "error" in result and result["error"]:
                                error_msg = result['error']
                                if "taking longer than expected" in error_msg:
                                    yield f"The calendar operation is taking a while. {error_msg} "
                                else:
                                    yield f"I encountered an issue: {error_msg} "
                            else:
                                # Parse result for user-friendly message
                                if "content" in result and isinstance(result["content"], list):
                                    for content in result["content"]:
                                        if content.get("type") == "text":
                                            try:
                                                # Try to parse the text as JSON for calendar results
                                                data = json.loads(content["text"])
                                                if "results" in data and data["results"]:
                                                    event = data["results"][0]
                                                    summary = event.get("summary", "event")
                                                    start = event.get("start", {})
                                                    start_time = start.get("time_pretty", start.get("dateTime_pretty", ""))
                                                    yield f"I've created '{summary}' for {start_time}. "
                                                else:
                                                    yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                                            except:
                                                yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                                else:
                                    yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                            
                            # Clear buffer after tool call
                            buffer = buffer[match.end():]
                        else:
                            yield buffer[:match.end()]
                            buffer = buffer[match.end():]
                            
                    except json.JSONDecodeError:
                        # Invalid JSON, just yield the text
                        yield buffer
                        buffer = ""
                else:
                    # No tool call found, yield text immediately for smoother streaming
                    # But first check if we might be in the middle of a tool call
                    if '```tool' in buffer and '```' not in buffer[buffer.find('```tool') + 7:]:
                        # We're in the middle of a tool call, don't yield yet
                        continue
                    
                    # Yield the entire buffer for smoother streaming
                    if buffer:
                        yield buffer
                        buffer = ""
        
        # Yield any remaining buffer
        if buffer:
            # Check one more time for tool calls in final buffer
            tool_pattern = r'```tool\n(.*?)\n```'
            match = re.search(tool_pattern, buffer, re.DOTALL)
            if match:
                # Process the tool call here
                try:
                    tool_json = match.group(1).strip()
                    print(f"Found tool call JSON: {tool_json}")
                    tool_call = json.loads(tool_json)
                    tool_name = tool_call.get("tool")
                    arguments = tool_call.get("arguments", {})
                    
                    print(f"Executing tool: {tool_name} with arguments: {arguments}")
                    
                    if mcp_client:
                        pre_tool_text = buffer[:match.start()]
                        if pre_tool_text:
                            yield pre_tool_text
                        else:
                            if "calendar" in tool_name and "create" in tool_name.lower():
                                yield "I'll create that calendar event for you. "
                            elif "calendar" in tool_name and "find" in tool_name.lower():
                                yield "Let me check your calendar. "
                            else:
                                yield f"Let me {tool_name.replace('_', ' ')} for you. "
                        
                        result = await mcp_client.call_tool(tool_name, arguments)
                        print(f"MCP call result: {result}")
                        
                        if "error" in result and result["error"]:
                            error_msg = result['error']
                            if "taking longer than expected" in error_msg:
                                yield f"The calendar operation is taking a while. {error_msg} "
                            else:
                                yield f"I encountered an issue: {error_msg} "
                        else:
                            if "content" in result and isinstance(result["content"], list):
                                for content in result["content"]:
                                    if content.get("type") == "text":
                                        try:
                                            data = json.loads(content["text"])
                                            if "results" in data and data["results"]:
                                                event = data["results"][0]
                                                summary = event.get("summary", "event")
                                                start = event.get("start", {})
                                                start_time = start.get("time_pretty", start.get("dateTime_pretty", ""))
                                                yield f"I've created '{summary}' for {start_time}. "
                                            else:
                                                yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                                        except:
                                            yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                            else:
                                yield f"I've successfully completed the {tool_name.replace('_', ' ')} action. "
                except Exception as e:
                    print(f"Error processing final buffer tool call: {e}")
                    yield buffer
            else:
                yield buffer
                
    except Exception as e:
        print(f"Error generating Gemini response: {str(e)}")
        yield "I'm sorry, I encountered an error while processing your request."

async def generate_tts_audio(text: str) -> str:
    """Generate TTS audio using ElevenLabs API"""
    if not ELEVENLABS_API_KEY:
        return None
    
    try:
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = AUDIO_DIR / f"{audio_id}.mp3"
        
        # Run the blocking ElevenLabs API call in a thread pool
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,  # Use default thread pool
            lambda: generate(
                api_key=ELEVENLABS_API_KEY,
                text=text,
                voice=ELEVENLABS_VOICE_ID,
                model="eleven_monolingual_v1"
            )
        )
        
        # Save audio to file (also in thread pool as it's I/O)
        await loop.run_in_executor(None, save, audio, str(audio_path))
        
        # Return URL path for the audio file
        return f"/audio/{audio_id}"
        
    except Exception as e:
        print(f"Error generating TTS audio: {str(e)}")
        return None

async def generate_and_queue_tts(websocket: WebSocket, text: str, gen_id: int, current_gen_id_ref, 
                                chunk_index: int, audio_queue: dict, audio_queue_lock: asyncio.Lock,
                                chunks_notifier: asyncio.Event):
    """Generate TTS and add to ordered queue"""
    try:
        # Check if this generation is still current before starting TTS
        if gen_id != current_gen_id_ref():
            print(f"TTS generation {gen_id} cancelled before starting")
            return
        
        # Use semaphore to limit concurrent TTS requests
        async with TTS_SEMAPHORE:
            print(f"[{time.time():.2f}] Acquired TTS semaphore for chunk {chunk_index}")
            start_time = time.time()
            audio_url = await generate_tts_audio(text)
            generation_time = time.time() - start_time
            print(f"[{time.time():.2f}] TTS generated in {generation_time:.2f}s for chunk {chunk_index}: {text[:50]}...")
        
        # Check again before queuing
        if gen_id != current_gen_id_ref():
            print(f"TTS generation {gen_id} cancelled before queuing")
            return
        
        # Add to queue and notify
        async with audio_queue_lock:
            audio_queue[chunk_index] = (audio_url, text) if audio_url else None
            print(f"[{time.time():.2f}] Added chunk {chunk_index} to queue")
        
        # Notify the audio sender that new chunks are available
        chunks_notifier.set()
            
    except asyncio.CancelledError:
        print(f"TTS generation {gen_id} cancelled")
    except Exception as e:
        print(f"Error in TTS generation: {e}")

async def send_queued_audio(websocket: WebSocket, audio_queue: dict, audio_queue_lock: asyncio.Lock, 
                           next_audio_to_send: list, gen_id: int, current_gen_id_ref, total_chunks: list,
                           chunks_notifier: asyncio.Event):
    """Send audio chunks in order as they become available"""
    
    while True:
        # Wait for notification that new chunks might be available
        await chunks_notifier.wait()
        chunks_notifier.clear()
        
        # Check for cancellation immediately after waking up
        if gen_id != current_gen_id_ref():
            print(f"Audio sender for generation {gen_id} stopping due to cancellation (after wake)")
            return
        
        # Process all available chunks
        while True:
            async with audio_queue_lock:
                # Check if we've sent all chunks
                if total_chunks[0] is not None and next_audio_to_send[0] >= total_chunks[0]:
                    print(f"[{time.time():.2f}] All {total_chunks[0]} audio chunks sent, stopping audio sender")
                    return
                
                # Check if next chunk is ready
                if next_audio_to_send[0] in audio_queue:
                    chunk_data = audio_queue.pop(next_audio_to_send[0])
                    current_index = next_audio_to_send[0]
                    next_audio_to_send[0] += 1
                    
                    if chunk_data is None:
                        # This chunk had no audio (maybe an error)
                        continue
                        
                    audio_url, text = chunk_data
                    print(f"[{time.time():.2f}] Sending audio chunk {current_index} to frontend: {text[:50]}...")
                    
                    # Send without holding the lock
                    sending_data = {
                        "type": "audio_chunk",
                        "audio_url": audio_url,
                        "text": text
                    }
                else:
                    # No more chunks ready
                    break
            
            # Check if cancelled before sending
            if gen_id != current_gen_id_ref():
                print(f"Audio sender for generation {gen_id} stopping due to cancellation (before send)")
                return
                
            # Send the audio chunk (outside the lock)
            if 'sending_data' in locals():
                try:
                    await websocket.send_json(sending_data)
                    print(f"[{time.time():.2f}] Audio chunk {current_index} sent successfully")
                    del sending_data
                except Exception as e:
                    print(f"Error sending audio chunk: {e}")
                    return
        
        # Check if we should stop due to cancellation
        if gen_id != current_gen_id_ref():
            print(f"Audio sender for generation {gen_id} stopping due to cancellation")
            return

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"WebSocket connection attempt from {websocket.client}")
    await websocket.accept()
    print("WebSocket connection accepted")
    
    # Initialize audio stream handler with current event loop
    loop = asyncio.get_event_loop()
    audio_handler = AudioStreamHandler(websocket, loop)
    await audio_handler.start()
    
    # Track active generation tasks
    active_tasks = set()
    current_generation_id = 0
    active_notifiers = []  # Track all chunk notifiers for interruption
    
    # Track conversation
    conversation = []
    
    try:
        print("Starting message loop...")
        while True:
            # Receive message from client (could be JSON or binary audio)
            message = await websocket.receive()
            
            if "text" in message:
                # JSON message
                data = json.loads(message["text"])
                print(f"Received: {data}")
                
                if data.get("type") == "audio_config":
                    # Client is configuring audio settings
                    print(f"Audio config received: {data}")
                    
                elif data.get("type") == "interrupt":
                    # Cancel all active tasks
                    print(f"Interruption received, cancelling {len(active_tasks)} active tasks...")
                    for task in active_tasks:
                        if not task.done():
                            task.cancel()
                    active_tasks.clear()
                    current_generation_id += 1  # Increment ID to invalidate old responses
                    
                    # Wake up all audio senders so they can check cancellation
                    for notifier in active_notifiers:
                        notifier.set()
                    active_notifiers.clear()
                    
            elif "bytes" in message:
                # Binary audio data
                audio_data = message["bytes"]
                await audio_handler.add_audio(audio_data)
                
                # Check for complete sentences
                sentence = await audio_handler.get_transcript()
                if sentence:
                    print(f"[MAIN] Complete sentence received: {sentence}")
                    
                    # Pause listening while we process the response
                    audio_handler.pause_listening()
                    
                    # Add to conversation
                    conversation.append({"role": "user", "content": sentence})
                    print(f"[MAIN] Added to conversation, total messages: {len(conversation)}")
                    
                    # Send sentence to client for display
                    await websocket.send_json({
                        "type": "user_transcript",
                        "text": sentence
                    })
                    print(f"[MAIN] Sent user_transcript to frontend")
                    
                    # Start streaming response
                    await websocket.send_json({
                        "type": "stream_start"
                    })
                    print(f"[MAIN] Sent stream_start to frontend")
                    
                    # Increment generation ID for this response
                    current_generation_id += 1
                    generation_id = current_generation_id
                    
                    # Create a task for the streaming response
                    async def stream_response(gen_id: int, notifiers_list: list, user_message: str):
                        print(f"[STREAM] stream_response started for gen_id {gen_id}, message: {user_message}")
                        # Check if this generation is still current
                        if gen_id != current_generation_id:
                            print(f"[STREAM] Generation {gen_id} cancelled before starting")
                            return
                            
                        # Buffer for accumulating text chunks
                        text_buffer = ""
                        full_response = ""
                        complete_sentences = []  # Store complete sentences
                        sentences_processed = 0  # Track sentences already processed for TTS
                        
                        # Audio queue to maintain order
                        audio_queue = {}  # chunk_index -> (audio_url, text) or None
                        next_audio_to_send = [0]  # Track which audio chunk to send next (list for mutability)
                        audio_queue_lock = asyncio.Lock()
                        chunk_counter = 0  # Counter for chunk indices
                        total_chunks = [None]  # Will be set when we know total chunks (list for mutability)
                        chunks_notifier = asyncio.Event()  # Event to notify when chunks are ready
                        notifiers_list.append(chunks_notifier)  # Track this notifier for interruption
                        
                        # Start the audio sender task
                        audio_sender_task = asyncio.create_task(
                            send_queued_audio(websocket, audio_queue, audio_queue_lock, 
                                            next_audio_to_send, generation_id, lambda: current_generation_id,
                                            total_chunks, chunks_notifier)
                        )
                        active_tasks.add(audio_sender_task)
                        audio_sender_task.add_done_callback(lambda t: active_tasks.discard(t))
                        
                        try:
                            async for text_chunk in generate_gemini_response_stream(user_message, conversation):
                                # Check if cancelled
                                if gen_id != current_generation_id:
                                    print(f"Generation {gen_id} cancelled during streaming")
                                    raise asyncio.CancelledError()
                                    
                                text_buffer += text_chunk
                                full_response += text_chunk
                        
                                # Send text chunk immediately
                                await websocket.send_json({
                                    "type": "text_chunk",
                                    "text": text_chunk,
                                    "timestamp": time.time()
                                })
                                print(f"[{time.time():.2f}] Sent text chunk: {text_chunk[:30]}...")
                                
                                # Log progress every 10 characters to reduce noise
                                if len(full_response) % 10 == 0:
                                    print(f"Progress: {len(full_response)} chars, {len(complete_sentences)} sentences complete, {sentences_processed} processed")
                                
                                # Skip TTS for tool calls
                                if '```tool' in text_buffer:
                                    # Don't process tool calls as sentences
                                    continue
                                
                                # Check for complete sentences (ending with . ! ?)
                                # Split but keep the delimiter
                                parts = re.split(r'([.!?]\s+)', text_buffer)
                        
                                # Reconstruct complete sentences
                                current_sentences = []
                                i = 0
                                while i < len(parts) - 1:
                                    if i + 1 < len(parts) and re.match(r'[.!?]\s+', parts[i + 1]):
                                        # Complete sentence found
                                        complete_sent = parts[i] + parts[i + 1].strip()
                                        current_sentences.append(complete_sent)
                                        i += 2
                                    else:
                                        i += 1
                                
                                # Update text buffer with remaining incomplete sentence
                                if i < len(parts):
                                    text_buffer = parts[i]
                                else:
                                    text_buffer = ""
                                
                                # Add new complete sentences to our list
                                complete_sentences.extend(current_sentences)
                                
                                # Process sentences with optimized chunking for minimal latency
                                while len(complete_sentences) - sentences_processed >= 1:
                                    # For the very first sentence, always process it alone for fastest time to first token
                                    if sentences_processed == 0:
                                        # Process first sentence individually
                                        chunk_sentences = complete_sentences[sentences_processed:sentences_processed + 1]
                                        sentences_processed += 1
                                    # After first sentence, process in 2-sentence chunks when possible
                                    elif len(complete_sentences) - sentences_processed >= 2:
                                        # Process 2 sentences if available
                                        chunk_sentences = complete_sentences[sentences_processed:sentences_processed + 2]
                                        sentences_processed += 2
                                    else:
                                        # Process single sentence if that's all we have left
                                        chunk_sentences = complete_sentences[sentences_processed:sentences_processed + 1]
                                        sentences_processed += 1
                                    chunk_text = ' '.join(chunk_sentences)
                                    
                                    if chunk_text.strip() and ELEVENLABS_API_KEY:
                                        # Check if still current before generating TTS
                                        if gen_id == current_generation_id:
                                            print(f"[{time.time():.2f}] Generating TTS for chunk {chunk_counter}: {chunk_text[:50]}...")
                                            # Run TTS generation in background to not block streaming
                                            tts_task = asyncio.create_task(
                                                generate_and_queue_tts(websocket, chunk_text, gen_id, lambda: current_generation_id,
                                                                     chunk_counter, audio_queue, audio_queue_lock, chunks_notifier)
                                            )
                                            active_tasks.add(tts_task)
                                            tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                                            chunk_counter += 1
                                            print(f"[{time.time():.2f}] TTS task created for chunk {chunk_counter-1}, {len(active_tasks)} active tasks")
                            
                            # Add any remaining text buffer as a final sentence (unless it's a tool call)
                            if text_buffer.strip() and '```tool' not in text_buffer:
                                complete_sentences.append(text_buffer)
                            
                            # Process any remaining unprocessed sentences
                            remaining_sentences = complete_sentences[sentences_processed:]
                            if remaining_sentences and ELEVENLABS_API_KEY:
                                # Process remaining sentences (could be 1 or 2)
                                chunk_text = ' '.join(remaining_sentences)
                                if chunk_text.strip() and '```tool' not in chunk_text:
                                    print(f"[{time.time():.2f}] Generating TTS for final chunk {chunk_counter}: {chunk_text[:50]}...")
                                    tts_task = asyncio.create_task(
                                        generate_and_queue_tts(websocket, chunk_text, gen_id, lambda: current_generation_id,
                                                             chunk_counter, audio_queue, audio_queue_lock, chunks_notifier)
                                    )
                                    active_tasks.add(tts_task)
                                    tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                                    chunk_counter += 1
                            
                            # Signal end of audio chunks
                            async with audio_queue_lock:
                                total_chunks[0] = chunk_counter
                                print(f"[{time.time():.2f}] Total chunks to send: {chunk_counter}")
                            
                            # Notify audio sender that we're done generating chunks
                            chunks_notifier.set()
                            
                            # Add complete response to conversation
                            conversation.append({"role": "assistant", "content": full_response})
                            
                            # Send stream complete
                            print("[MAIN] Sending stream_complete")
                            await websocket.send_json({
                                "type": "stream_complete",
                                "full_text": full_response
                            })
                            print("[MAIN] stream_complete sent successfully")
                            
                            # Resume listening for user input
                            print("[MAIN] About to call audio_handler.resume_listening()")
                            audio_handler.resume_listening()
                            print("[MAIN] audio_handler.resume_listening() called successfully")
                        except asyncio.CancelledError:
                            print("Stream cancelled due to interruption")
                            # Send partial response complete
                            await websocket.send_json({
                                "type": "stream_complete",
                                "full_text": full_response,
                                "interrupted": True
                            })
                            # Resume listening after interruption
                            audio_handler.resume_listening()
                            raise
                        finally:
                            # Clean up notifier
                            if chunks_notifier in notifiers_list:
                                notifiers_list.remove(chunks_notifier)
                    
                    # Run the streaming in a task so it can be cancelled
                    print("[MAIN] Creating stream_response task")
                    stream_task = asyncio.create_task(stream_response(generation_id, active_notifiers, sentence))
                    active_tasks.add(stream_task)
                    stream_task.add_done_callback(lambda t: active_tasks.discard(t))
                    
                    # Wait for the task to complete
                    try:
                        print("[MAIN] Waiting for stream_task to complete")
                        await stream_task
                        print("[MAIN] stream_task completed successfully")
                    except asyncio.CancelledError:
                        print("[MAIN] stream_task was cancelled")
                    except Exception as e:
                        print(f"[MAIN] stream_task failed with error: {e}")
                        import traceback
                        traceback.print_exc()
                    
    except WebSocketDisconnect:
        print("Client disconnected normally")
        await audio_handler.stop()
    except Exception as e:
        print(f"WebSocket error: {type(e).__name__}: {e}")
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
    print(f"Serving audio file: {audio_path}")
    
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/mpeg")
    else:
        print(f"Audio file not found: {audio_path}")
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
    
    # Initialize MCP client
    global mcp_client
    try:
        mcp_client = MCPClient(MCP_URL)
        await mcp_client.initialize()
        print("MCP client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")
        mcp_client = None

@app.on_event("shutdown")
async def shutdown_event():
    # Close MCP client
    global mcp_client
    if mcp_client:
        await mcp_client.close()
        print("MCP client closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")