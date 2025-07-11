"""WebSocket route for real-time audio streaming"""
import asyncio
import json
import re
import time
from fastapi import WebSocket, WebSocketDisconnect
from handlers.audio_stream_handler import AudioStreamHandler
from services.gemini_service import generate_gemini_response_stream
from services.elevenlabs_service import generate_tts_audio_fast
from utils.helpers import timestamp
from routes.agents import agents_db


async def websocket_endpoint(websocket: WebSocket):
    print(f"\n{timestamp()} 🔌 WebSocket connection from {websocket.client}")
    await websocket.accept()
    print(f"{timestamp()} ✓ WebSocket connected")
    
    # Initialize audio stream handler with current event loop
    loop = asyncio.get_event_loop()
    audio_handler = AudioStreamHandler(websocket, loop)
    
    # Track active generation tasks
    active_tasks = set()
    current_generation_id = 0
    active_stream_task = None  # Track the current active stream task to prevent duplicates
    
    # Define interrupt handler
    async def handle_interrupt():
        nonlocal current_generation_id, active_stream_task
        print(f"{timestamp()} 🛑 Voice activity interrupt - cancelling {len(active_tasks)} tasks")
        for task in active_tasks:
            if not task.done():
                task.cancel()
        active_tasks.clear()
        active_stream_task = None  # Clear active stream task
        current_generation_id += 1  # Increment ID to invalidate old responses
        
        # Ensure system is ready to continue conversation after interruption
        print(f"{timestamp()} 🔄 Post-interruption cleanup: ensuring system is ready for new conversation")
        await websocket.send_json({
            "type": "interruption_complete",
            "timestamp": time.time()
        })
    
    # Set the interrupt callback
    audio_handler.set_interrupt_callback(handle_interrupt)
    await audio_handler.start()
    
    # Track conversation and agent info
    conversation = []
    current_agent = None
    
    # Create a task to continuously check for transcripts
    async def process_transcripts():
        """Continuously check for and process transcripts"""
        nonlocal current_generation_id, active_stream_task
        while True:
            try:
                # Check for complete transcripts
                transcript = await audio_handler.get_transcript()
                if transcript:
                    # Clear any additional queued transcripts to ensure we only process the latest
                    while not audio_handler.transcript_queue.empty():
                        try:
                            old_transcript = audio_handler.transcript_queue.get_nowait()
                            print(f"{timestamp()} ⏭️  Skipping queued transcript: '{old_transcript[:50]}...'")
                        except asyncio.QueueEmpty:
                            break
                    print(f"\n{timestamp()} 🔄 NEW CONVERSATION TURN STARTING")
                    print(f"{timestamp()} 📋 Conversation state: listening={audio_handler.is_listening_for_user}, agent_speaking={audio_handler.is_agent_speaking}, interrupting={audio_handler.is_interrupting}")
                    
                    response_pipeline_start = time.time()
                    # Calculate delay from speech end
                    if audio_handler.speech_start_time:
                        transcript_delay = response_pipeline_start - audio_handler.speech_start_time
                        print(f"{timestamp()} 📝 Transcript: '{transcript}' (received {transcript_delay:.2f}s after speech start)")
                    else:
                        print(f"{timestamp()} 📝 Transcript: '{transcript}'")
                    print(f"{timestamp()} ⏱️  Starting response pipeline...")
                    
                    # Add to conversation
                    conversation.append({"role": "user", "content": transcript})
                    
                    # Pause listening while we process the response
                    audio_handler.pause_listening()
                    
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
                            first_audio_time = None  # Initialize to avoid UnboundLocalError
                            
                            # Track timing
                            llm_start = time.time()
                            
                            # Double-check we're still current before starting LLM
                            if gen_id != current_generation_id:
                                print(f"{timestamp()} ⏭️  Skipping LLM call - generation ID mismatch")
                                return
                                
                            async for text_chunk in generate_gemini_response_stream(transcript, conversation, current_agent):
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
                                        print(f"{timestamp()} 🎯 First sentence ready, starting TTS for: '{first_sentence[:50]}...'")
                                        print(f"{timestamp()} 📊 Generation ID: {gen_id}, Current ID: {current_generation_id}")
                                        first_tts_task = asyncio.create_task(
                                            generate_tts_audio_fast(first_sentence)
                                        )
                                        active_tasks.add(first_tts_task)
                                        first_tts_task.add_done_callback(lambda t: active_tasks.discard(t))
                            
                            # Wait for first TTS if we have one
                            if first_tts_task:
                                audio_url = await first_tts_task
                                if audio_url and gen_id == current_generation_id:
                                    first_audio_time = time.time() - response_pipeline_start
                                    print(f"{timestamp()} 🎉 First audio ready in {first_audio_time:.2f}s from user stop")
                                    
                                    # Mark that agent is speaking
                                    audio_handler.set_agent_speaking(True)
                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "audio_url": audio_url,
                                        "text": first_sentence,
                                        "timestamp": time.time()
                                    })
                                elif gen_id != current_generation_id:
                                    print(f"{timestamp()} ⏭️  Skipping audio - generation ID mismatch ({gen_id} != {current_generation_id})")
                            
                            # Generate TTS for remaining text if any
                            remaining_text = full_response[len(first_sentence):].strip()
                            if remaining_text and remaining_text not in ["", "."]:
                                print(f"{timestamp()} 🔊 TTS: Generating remaining audio")
                                remaining_audio_url = await generate_tts_audio_fast(remaining_text)
                                if remaining_audio_url and gen_id == current_generation_id:
                                    # Mark that agent is speaking (in case first chunk didn't exist)
                                    audio_handler.set_agent_speaking(True)
                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "audio_url": remaining_audio_url,
                                        "text": remaining_text,
                                        "timestamp": time.time()
                                    })
                                elif gen_id != current_generation_id:
                                    print(f"{timestamp()} ⏭️  Skipping remaining audio - generation ID mismatch")
                            
                            # Add complete response to conversation
                            if gen_id == current_generation_id:
                                conversation.append({"role": "assistant", "content": full_response})
                            
                            # Send stream complete
                            await websocket.send_json({
                                "type": "stream_complete",
                                "full_text": full_response,
                                "timestamp": time.time()
                            })
                            
                            total_time = time.time() - response_pipeline_start
                            print(f"{timestamp()} ✅ Response pipeline complete in {total_time:.2f}s")
                            
                            # Calculate actual user-perceived delay - only if we have audio timing
                            if audio_handler.speech_start_time and first_audio_time is not None:
                                print(f"{timestamp()} 📊 Timing Breakdown:")
                                print(f"    • Speech duration: {(response_pipeline_start - audio_handler.speech_start_time):.2f}s")
                                print(f"    • VAD prefetch @ 200ms, confirm @ 800ms")  
                                print(f"    • Whisper: ~0.6s (prefetched)")
                                print(f"    • LLM first token: {(llm_start - response_pipeline_start):.2f}s")
                                print(f"    • TTS generation: {(first_audio_time - (llm_start - response_pipeline_start)):.2f}s")
                                print(f"    • 🎯 Total delay (speech end → audio): {first_audio_time:.2f}s\n")
                            elif first_audio_time is not None:
                                print(f"{timestamp()} 📊 Standard Breakdown:")
                                print(f"    • VAD + Whisper: ~0.8s (speculative)")
                                print(f"    • LLM first token: {(llm_start - response_pipeline_start):.2f}s")
                                print(f"    • TTS generation: {(first_audio_time - (llm_start - response_pipeline_start)):.2f}s")
                                print(f"    • Total: {total_time:.2f}s\n")
                            else:
                                print(f"{timestamp()} 📊 No audio generated - text-only response ({total_time:.2f}s)\n")
                            
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
                    
                    # Cancel any existing stream task if it's still running
                    if active_stream_task and not active_stream_task.done():
                        print(f"{timestamp()} ⚠️  Cancelling previous stream task")
                        active_stream_task.cancel()
                        try:
                            await active_stream_task
                        except asyncio.CancelledError:
                            pass
                    
                    # Run the streaming in a task
                    stream_task = asyncio.create_task(stream_response(generation_id))
                    active_stream_task = stream_task  # Track as active stream
                    active_tasks.add(stream_task)
                    stream_task.add_done_callback(lambda t: active_tasks.discard(t))
                    
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        print(f"{timestamp()} 🔄 Stream task cancelled")
                        pass
                    except Exception as e:
                        print(f"{timestamp()} ❌ Stream error: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        # Clear active stream task when done
                        if active_stream_task == stream_task:
                            active_stream_task = None
                        
            except Exception as e:
                print(f"{timestamp()} ❌ Transcript processing error: {e}")
                import traceback
                traceback.print_exc()
            
            # Small delay to prevent busy loop
            await asyncio.sleep(0.01)
    
    # Start the transcript processing task
    transcript_task = asyncio.create_task(process_transcripts())
    
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
                    
                elif data.get("type") == "agent_config":
                    # Client is setting agent configuration
                    agent_id = data.get("agent_id")
                    if agent_id and agent_id in agents_db:
                        current_agent = agents_db[agent_id]
                        print(f"{timestamp()} 🤖 Agent configured: {current_agent['name']}")
                    
                elif data.get("type") == "call_started":
                    # User started the call - send greeting if configured
                    print(f"{timestamp()} 📞 Call started")
                    
                    if current_agent and current_agent.get("greeting"):
                        # Add greeting to conversation history
                        conversation.append({"role": "assistant", "content": current_agent["greeting"]})
                        
                        # Send greeting to frontend
                        await websocket.send_json({
                            "type": "agent_greeting",
                            "text": current_agent["greeting"],
                            "timestamp": time.time()
                        })
                        
                        # Generate TTS for greeting
                        greeting_audio_url = await generate_tts_audio_fast(current_agent["greeting"])
                        if greeting_audio_url:
                            # Pause listening while agent speaks greeting
                            audio_handler.pause_listening()
                            # Mark agent as speaking before sending audio
                            audio_handler.set_agent_speaking(True)
                            await websocket.send_json({
                                "type": "greeting_audio",
                                "audio_url": greeting_audio_url,
                                "timestamp": time.time()
                            })
                    
                elif data.get("type") == "audio_playback_complete":
                    # Frontend finished playing audio
                    print(f"{timestamp()} 🔇 Audio playback complete")
                    audio_handler.set_agent_speaking(False)
                    # Resume listening after any audio playback (greeting or response)
                    audio_handler.resume_listening()
                    
                elif data.get("type") == "interrupt":
                    # Cancel all active tasks
                    reason = data.get("reason", "unknown")
                    print(f"{timestamp()} 🛑 Interruption ({reason}) - cancelling {len(active_tasks)} tasks")
                    for task in active_tasks:
                        if not task.done():
                            task.cancel()
                    active_tasks.clear()
                    current_generation_id += 1  # Increment ID to invalidate old responses
                    
            elif "bytes" in message:
                # Binary audio data
                audio_data = message["bytes"]
                await audio_handler.add_audio(audio_data)
                    
    except WebSocketDisconnect:
        print(f"{timestamp()} 🔌 Client disconnected")
        transcript_task.cancel()
        await audio_handler.stop()
    except Exception as e:
        print(f"{timestamp()} ❌ WebSocket error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        transcript_task.cancel()
        await audio_handler.stop()