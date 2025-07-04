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
from elevenlabs import generate, save, stream
import uuid
import re
import io
import time
from mcp_client import MCPClient

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
    print(GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("Warning: GEMINI_API_KEY not found in environment variables")
    model = None

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
    return {"message": "Voice Agent API"}

async def generate_and_send_tts(websocket: WebSocket, text: str, gen_id: int, current_gen_id_ref):
    """Generate TTS and send to client asynchronously"""
    try:
        # Check if this generation is still current before starting TTS
        if gen_id != current_gen_id_ref():
            print(f"TTS generation {gen_id} cancelled before starting")
            return
            
        start_time = time.time()
        audio_url = await generate_tts_audio(text)
        generation_time = time.time() - start_time
        print(f"TTS generated in {generation_time:.2f}s for: {text[:50]}...")
        
        # Check again before sending
        if gen_id != current_gen_id_ref():
            print(f"TTS generation {gen_id} cancelled before sending")
            return
        
        if audio_url:
            await websocket.send_json({
                "type": "audio_chunk",
                "audio_url": audio_url,
                "text": text
            })
    except asyncio.CancelledError:
        print(f"TTS generation {gen_id} cancelled")
    except Exception as e:
        print(f"Error in TTS generation: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"WebSocket connection attempt from {websocket.client}")
    await websocket.accept()
    print("WebSocket connection accepted")
    
    # Track active generation tasks
    active_tasks = set()
    current_generation_id = 0
    
    try:
        print("Starting message loop...")
        while True:
            # Receive message from client
            print("Waiting for message...")
            data = await websocket.receive_json()
            print(f"Received: {data}")
            
            if data.get("type") == "interrupt":
                # Cancel all active tasks
                print(f"Interruption received, cancelling {len(active_tasks)} active tasks...")
                for task in active_tasks:
                    if not task.done():
                        task.cancel()
                active_tasks.clear()
                current_generation_id += 1  # Increment ID to invalidate old responses
                
            elif data.get("type") == "message":
                user_message = data["content"]
                conversation = data.get("conversation", [])
                
                print(f"\n=== Received message ===")
                print(f"User message: {user_message}")
                print(f"Conversation history ({len(conversation)} messages):")
                for i, msg in enumerate(conversation):
                    print(f"  {i}: {msg['role']}: {msg['content'][:50]}...")
                print("========================\n")
                
                # Start streaming response
                await websocket.send_json({
                    "type": "stream_start"
                })
                
                # Increment generation ID for this response
                current_generation_id += 1
                generation_id = current_generation_id
                
                # Create a task for the streaming response
                async def stream_response(gen_id: int):
                    # Check if this generation is still current
                    if gen_id != current_generation_id:
                        print(f"Generation {gen_id} cancelled before starting")
                        return
                        
                    # Buffer for accumulating text chunks
                    text_buffer = ""
                    full_response = ""
                    complete_sentences = []  # Store complete sentences
                    sentences_processed = 0  # Track sentences already processed for TTS
                    
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
                                "text": text_chunk
                            })
                            
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
                                    sentence = parts[i] + parts[i + 1].strip()
                                    current_sentences.append(sentence)
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
                            
                            # Process sentences as soon as we have 1 for faster audio start
                            # Will process in pairs when we have 2, or single if that's all we have
                            while len(complete_sentences) - sentences_processed >= 1:
                                # Get the next 1-2 unprocessed sentences
                                if len(complete_sentences) - sentences_processed >= 2:
                                    # Process 2 sentences if available
                                    chunk_sentences = complete_sentences[sentences_processed:sentences_processed + 2]
                                    sentences_processed += 2
                                else:
                                    # Process single sentence for faster start
                                    chunk_sentences = complete_sentences[sentences_processed:sentences_processed + 1]
                                    sentences_processed += 1
                                chunk_text = ' '.join(chunk_sentences)
                                
                                if chunk_text.strip() and ELEVENLABS_API_KEY:
                                    # Check if still current before generating TTS
                                    if gen_id == current_generation_id:
                                        print(f"Generating TTS for: {chunk_text[:50]}...")
                                        # Run TTS generation in background to not block streaming
                                        tts_task = asyncio.create_task(generate_and_send_tts(websocket, chunk_text, gen_id, lambda: current_generation_id))
                                        active_tasks.add(tts_task)
                                        tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                        
                        # Add any remaining text buffer as a final sentence (unless it's a tool call)
                        if text_buffer.strip() and '```tool' not in text_buffer:
                            complete_sentences.append(text_buffer)
                        
                        # Process any remaining unprocessed sentences
                        remaining_sentences = complete_sentences[sentences_processed:]
                        if remaining_sentences and ELEVENLABS_API_KEY:
                            # Process remaining sentences (could be 1 or 2)
                            chunk_text = ' '.join(remaining_sentences)
                            if chunk_text.strip() and '```tool' not in chunk_text:
                                print(f"Generating TTS for final chunk: {chunk_text[:50]}...")
                                tts_task = asyncio.create_task(generate_and_send_tts(websocket, chunk_text, gen_id, lambda: current_generation_id))
                                active_tasks.add(tts_task)
                                tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                        
                        # Send stream complete
                        await websocket.send_json({
                            "type": "stream_complete",
                            "full_text": full_response
                        })
                    except asyncio.CancelledError:
                        print("Stream cancelled due to interruption")
                        # Send partial response complete
                        await websocket.send_json({
                            "type": "stream_complete",
                            "full_text": full_response,
                            "interrupted": True
                        })
                        raise
                
                # Run the streaming in a task so it can be cancelled
                stream_task = asyncio.create_task(stream_response(generation_id))
                active_tasks.add(stream_task)
                stream_task.add_done_callback(lambda t: active_tasks.discard(t))
                
                # Wait for the task to complete
                try:
                    await stream_task
                except asyncio.CancelledError:
                    print("Main stream task cancelled")
                
    except WebSocketDisconnect:
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def generate_gemini_response_stream(user_message: str, conversation: list):
    """Generate streaming response using Google Gemini API"""
    if not model:
        yield "I'm sorry, but the AI model is not configured. Please check your API keys."
        return
    
    try:
        # Format conversation history for Gemini
        prompt = "You are a helpful voice assistant with access to external tools. Keep responses concise and conversational. Start your response immediately without any preamble.\n\n"
        prompt += "When a user asks you to create a calendar event, CREATE IT IMMEDIATELY using the tools, even if they don't provide all details. If no time is specified, use 'tomorrow at 2pm'. If no title is specified, use 'Meeting' or 'Appointment'. Never ask for more details - just create the event with sensible defaults.\n"
        prompt += f"Today's date is {datetime.now().strftime('%Y-%m-%d')}. When creating test events, use tomorrow or a future date.\n\n"
        
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
                    # No tool call found, yield text up to last newline
                    # But first check if we might be in the middle of a tool call
                    if '```tool' in buffer and '```' not in buffer[buffer.find('```tool') + 7:]:
                        # We're in the middle of a tool call, don't yield yet
                        continue
                    
                    last_newline = buffer.rfind('\n')
                    if last_newline > -1:
                        yield buffer[:last_newline + 1]
                        buffer = buffer[last_newline + 1:]
                    elif len(buffer) > 100:  # Prevent buffer from growing too large
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
        return f"/audio/{audio_id}"
        
    except Exception as e:
        print(f"Error generating TTS audio: {str(e)}")
        return None

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
    uvicorn.run(app, host="0.0.0.0", port=8000)