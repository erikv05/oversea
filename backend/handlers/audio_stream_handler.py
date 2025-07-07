"""Audio stream handler with Voice Activity Detection"""
import asyncio
import time
from typing import Optional
from fastapi import WebSocket
import webrtcvad
from config.settings import VAD_CONFIG
from services.deepgram_service import transcribe_audio
from utils.helpers import timestamp


class AudioStreamHandler:
    """Handles streaming audio with aggressive Voice Activity Detection for speed"""
    
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop
        self.is_running = True
        self.is_listening_for_user = True
        self.interrupt_callback = None  # Callback for interruptions
        self.is_agent_speaking = False  # Track if agent audio is playing
        self.is_interrupting = False  # Track if user is interrupting agent
        
        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad()
        # Set aggressiveness mode (0-3, where 3 is most aggressive)
        # Mode 3 is most aggressive at filtering out non-speech sounds
        self.vad.set_mode(3)
        
        # Voice Activity Detection parameters
        self.speech_buffer = bytearray()  # Buffer for current speech segment
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        
        # Pre-speech circular buffer
        self.pre_speech_buffer_size = VAD_CONFIG["pre_speech_buffer_size"]
        self.pre_speech_buffer = bytearray()
        
        # WebRTC VAD frame configuration
        # WebRTC VAD works with 10, 20, or 30ms frames at 8, 16, 32, or 48 kHz
        self.frame_duration_ms = 30  # Use 30ms frames
        self.frame_size = int(8000 * self.frame_duration_ms / 1000) * 2  # bytes for 30ms at 8kHz, 16-bit
        
        # Adjusted thresholds for WebRTC VAD
        self.speech_start_frames = 2  # 60ms of speech to start (2 * 30ms)
        self.speech_prefetch_frames = 7  # ~200ms of silence (7 * 30ms)
        self.speech_confirm_frames = 27  # ~800ms of silence (27 * 30ms)
        
        # Minimum speech duration
        self.min_speech_duration = VAD_CONFIG["min_speech_duration"]
        
        # Audio accumulator for frame alignment
        self.audio_accumulator = bytearray()
        
        # Speculative processing
        self.speculative_task = None
        self.is_speculating = False
        self.speculative_transcript = None
        self.speech_confirmed = False
        
        # Transcript handling
        self.transcript_queue = asyncio.Queue()
        self.processing_task = None
        
        # Performance tracking
        self.speech_start_time = None
        
    def set_interrupt_callback(self, callback):
        """Set the callback function for interruptions"""
        self.interrupt_callback = callback
        
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
        """Process incoming audio data with WebRTC VAD"""
        if not self.is_running:
            return
        
        # Add incoming audio to accumulator
        self.audio_accumulator.extend(audio_data)
        
        # Process accumulated audio in chunks suitable for WebRTC VAD
        while len(self.audio_accumulator) >= self.frame_size:
            # Extract frame
            frame = bytes(self.audio_accumulator[:self.frame_size])
            self.audio_accumulator = self.audio_accumulator[self.frame_size:]
            
            # Always add to pre-speech buffer (circular buffer)
            self._add_to_pre_speech_buffer(frame)
            
            # Run WebRTC VAD on the frame
            try:
                is_speech = self.vad.is_speech(frame, 8000)
            except Exception as e:
                print(f"{timestamp()} ⚠️  VAD error: {e}")
                is_speech = False
            
            # Voice Activity Detection logic using WebRTC VAD
            if is_speech:
                # --- IMMEDIATE INTERRUPTION --- 
                # If agent is speaking, interrupt immediately on any speech detection
                if self.is_agent_speaking and not self.is_interrupting:
                    self.is_interrupting = True
                    print(f"{timestamp()} 🛑 User started speaking while agent is active - interrupting")
                    print(f"{timestamp()} 📤 Sending stop_audio_immediately message to frontend")
                    
                    # Send message to stop audio playback on the frontend
                    await self.websocket.send_json({
                        "type": "stop_audio_immediately", 
                        "timestamp": time.time()
                    })
                    
                    # Cancel backend tasks
                    if self.interrupt_callback:
                        await self.interrupt_callback()

                    # Notify frontend of the interruption
                    await self.websocket.send_json({
                        "type": "user_interruption",
                        "timestamp": time.time()
                    })
                    
                    # CRITICAL: Resume listening immediately so interrupting speech can be processed as new query
                    self.is_listening_for_user = True
                    print(f"{timestamp()} ▶️  Listening to interrupting speech (will process as new query)")
                elif self.is_agent_speaking and self.is_interrupting:
                    # Already interrupting, just continue
                    pass
                elif not self.is_agent_speaking:
                    # Normal speech while agent is not speaking - continue to regular detection
                    pass
                else:
                    print(f"{timestamp()} 🔍 DEBUG: Speech detected but no interruption (agent_speaking={self.is_agent_speaking}, interrupting={self.is_interrupting})")

                # --- REGULAR SPEECH DETECTION ---
                self.speech_counter += 1
                self.silence_counter = 0
                
                # Use faster detection for interruptions vs normal speech
                required_frames = 1 if self.is_agent_speaking else self.speech_start_frames
                
                if not self.is_speaking and self.speech_counter >= required_frames:
                    # Start of speech detected
                    self.is_speaking = True
                    self.speech_start_time = time.time()
                    print(f"{timestamp()} 🎤 Speech started (WebRTC VAD)")
                    
                    # Cancel any speculative processing if user resumes speaking
                    if self.speculative_task and not self.speculative_task.done():
                        print(f"{timestamp()} ❌ Cancelling prefetch - user resumed speaking")
                        self.speculative_task.cancel()
                        self.is_speculating = False
                    
                    # Clear any speculative transcript
                    self.speculative_transcript = None
                    self.speech_confirmed = False
                    
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
                    
                    # Start prefetch after ~200ms of silence (only if listening for user)
                    if self.silence_counter == self.speech_prefetch_frames and self.is_listening_for_user:
                        if len(self.speech_buffer) > self.min_speech_duration and not self.is_speculating:
                            self.is_speculating = True
                            buffer_size_ms = len(self.speech_buffer) / 16
                            print(f"{timestamp()} 🔮 Starting prefetch (~200ms silence, {buffer_size_ms:.0f}ms audio)")
                            
                            # Start prefetch task
                            self.speculative_task = asyncio.create_task(
                                self._prefetch_process(bytes(self.speech_buffer))
                            )
                    
                    # Confirm speech ended after ~800ms total silence
                    if self.silence_counter >= self.speech_confirm_frames:
                        self.is_speaking = False
                        self.speech_confirmed = True
                        speech_duration = time.time() - self.speech_start_time
                        buffer_size_ms = len(self.speech_buffer) / 16
                        print(f"{timestamp()} ✅ Speech confirmed ended (~800ms silence, duration: {speech_duration:.2f}s)")
                        
                        # Process all speech as queries when listening for user input
                        if self.is_listening_for_user and len(self.speech_buffer) > self.min_speech_duration:
                            if self.is_interrupting:
                                print(f"{timestamp()} 🔄 Processing interrupting speech as new query")
                                self.is_interrupting = False
                            
                            # Process transcript (interrupting or normal)
                            if self.speculative_transcript:
                                print(f"{timestamp()} 🎯 Using prefetched transcript: '{self.speculative_transcript}'")
                                await self._commit_transcript(self.speculative_transcript)
                                self.speculative_transcript = None
                            else:
                                # No prefetch available, process normally
                                print(f"{timestamp()} 📝 No prefetch available, processing normally")
                                await self._process_speech_segment(bytes(self.speech_buffer))
                        elif self.is_interrupting:
                            # Just reset interruption state if not listening
                            print(f"{timestamp()} 🔇 Interruption speech ended - not listening for user input")
                            self.is_interrupting = False
                        else:
                            print(f"{timestamp()} 🔇 Not listening for user input")
                        
                        # Clear state
                        self.speech_buffer.clear()
                        self.is_speculating = False
                        self.speech_confirmed = False
                        
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
        
        transcript_text = await transcribe_audio(audio_data)
        
        if transcript_text:
            # Send transcript to frontend
            await self.websocket.send_json({
                "type": "user_transcript",
                "text": transcript_text,
                "timestamp": time.time()
            })
            
            # Add to queue for processing
            await self.transcript_queue.put(transcript_text)
    
    async def _prefetch_process(self, audio_data: bytes):
        """Prefetch transcription after 200ms but don't commit until confirmed"""
        try:
            prefetch_start = time.time()
            print(f"{timestamp()} 🔮 [1/2] Starting prefetch transcription")
            
            # Start transcription immediately
            transcript_text = await transcribe_audio(audio_data)
            
            if transcript_text:
                transcribe_time = time.time() - prefetch_start
                print(f"{timestamp()} 🔮 [2/2] Prefetch ready: '{transcript_text}' ({transcribe_time:.2f}s)")
                
                # Store the transcript but don't send it yet
                self.speculative_transcript = transcript_text
            else:
                print(f"{timestamp()} 🔮 Prefetch failed - no valid transcript")
                
        except asyncio.CancelledError:
            print(f"{timestamp()} 🔮 Prefetch cancelled - user resumed speaking")
            self.speculative_transcript = None
            raise
        except Exception as e:
            print(f"{timestamp()} ❌ Prefetch error: {e}")
            self.speculative_transcript = None
    
    async def _commit_transcript(self, transcript_text: str):
        """Commit a prefetched transcript once speech is confirmed ended"""
        # Send transcript to frontend
        await self.websocket.send_json({
            "type": "user_transcript",
            "text": transcript_text,
            "timestamp": time.time()
        })
        
        # Add to queue for processing
        await self.transcript_queue.put(transcript_text)
    
    def pause_listening(self):
        """Pause processing user speech (during agent response)"""
        print(f"{timestamp()} ⏸️  Pausing user speech processing (agent speaking)")
        self.is_listening_for_user = False
        # Reset counters so interruption detection works immediately
        self.speech_counter = 0
        self.silence_counter = 0
        
    def resume_listening(self):
        """Resume processing user speech (after agent response)"""
        print(f"{timestamp()} ▶️  Resuming user speech processing")
        self.is_listening_for_user = True
        # NOTE: Do NOT reset is_agent_speaking here! 
        # Agent speaking state should only be controlled by audio playback completion
        self.is_interrupting = False
        # Clear any buffered audio and speculative state
        self.speech_buffer.clear()
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        self.speculative_transcript = None
        self.speech_confirmed = False
        self.is_speculating = False
        
    def set_agent_speaking(self, speaking: bool):
        """Set whether the agent is currently speaking"""
        if self.is_agent_speaking != speaking:
            print(f"{timestamp()} 🎧 Agent speaking state: {self.is_agent_speaking} → {speaking}")
        self.is_agent_speaking = speaking
        if not speaking:
            # Reset interruption state when agent stops speaking
            self.is_interrupting = False
            print(f"{timestamp()} ✅ Ready for user input (agent finished speaking)")
        
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