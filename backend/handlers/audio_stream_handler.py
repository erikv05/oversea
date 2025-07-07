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
        self.interrupt_frames = 10  # 300ms of speech required to interrupt agent (10 * 30ms)
        
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
        
        # Interruption detection buffer
        self.interrupt_buffer = bytearray()  # Store recent frames for interruption detection
        
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
                # Speech detected
                self.speech_counter += 1
                self.silence_counter = 0
                
                # During agent speech, accumulate potential interruption audio
                if not self.is_listening_for_user:
                    # Add frame to interruption buffer
                    self.interrupt_buffer.extend(frame)
                    # Keep only recent frames (last 300ms)
                    max_interrupt_buffer = self.frame_size * 10  # 10 frames = 300ms
                    if len(self.interrupt_buffer) > max_interrupt_buffer:
                        self.interrupt_buffer = self.interrupt_buffer[-max_interrupt_buffer:]
                    
                    # Debug: log when we detect voice during agent speech
                    if self.speech_counter <= self.interrupt_frames:
                        print(f"{timestamp()} 🎤 Voice detected during agent speech - frame {self.speech_counter}/{self.interrupt_frames} (WebRTC VAD)")
                    
                    # Require multiple consecutive frames of speech to trigger interruption
                    # This helps filter out brief noises like table bangs
                    if self.speech_counter == self.interrupt_frames:
                        print(f"{timestamp()} 🛑 User interruption detected after {self.interrupt_frames} frames ({self.interrupt_frames * self.frame_duration_ms}ms) (WebRTC VAD)")
                        print(f"{timestamp()} 📤 Sending stop_audio_immediately message to frontend")
                        # IMMEDIATELY tell frontend to stop audio playback
                        await self.websocket.send_json({
                            "type": "stop_audio_immediately", 
                            "timestamp": time.time()
                        })
                        # Call the interrupt callback to cancel backend tasks
                        if self.interrupt_callback:
                            await self.interrupt_callback()
                        # Notify about the interruption
                        await self.websocket.send_json({
                            "type": "user_interruption",
                            "timestamp": time.time()
                        })
                        # Mark that we're in interruption mode
                        self.is_interrupting = True
                        # Resume listening BUT in interruption mode
                        self.is_listening_for_user = True
                        print(f"{timestamp()} ▶️  Listening to interrupting speech (will not process as new query)")
                        # Clear interruption buffer
                        self.interrupt_buffer.clear()
                
                if not self.is_speaking and self.speech_counter >= self.speech_start_frames:
                    # Start of speech detected
                    self.is_speaking = True
                    self.speech_start_time = time.time()
                    print(f"{timestamp()} 🎤 Speech started (WebRTC VAD)")
                    
                    # Check if agent is currently speaking/playing audio
                    if self.is_agent_speaking and not self.is_interrupting:
                        print(f"{timestamp()} 🛑 User started speaking while agent is active - interrupting")
                        print(f"{timestamp()} 📤 Sending stop_audio_immediately message to frontend")
                        # IMMEDIATELY tell frontend to stop audio playback
                        await self.websocket.send_json({
                            "type": "stop_audio_immediately", 
                            "timestamp": time.time()
                        })
                        # Call the interrupt callback to cancel backend tasks
                        if self.interrupt_callback:
                            await self.interrupt_callback()
                        # Notify about the interruption
                        await self.websocket.send_json({
                            "type": "user_interruption",
                            "timestamp": time.time()
                        })
                        # Mark that we're in interruption mode
                        self.is_interrupting = True
                        print(f"{timestamp()} ▶️  Listening to interrupting speech (will not process as new query)")
                    
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
                
                # Clear interrupt buffer when silence detected during agent speech
                if not self.is_listening_for_user:
                    self.interrupt_buffer.clear()
                
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
                        
                        # Check if this was an interruption or a new query
                        if self.is_interrupting:
                            print(f"{timestamp()} 🔇 Interruption speech ended - not processing as new query")
                            self.is_interrupting = False
                            # Stay listening for new queries
                        elif self.is_listening_for_user:
                            # Normal user query - process transcript
                            if self.speculative_transcript:
                                print(f"{timestamp()} 🎯 Using prefetched transcript: '{self.speculative_transcript}'")
                                await self._commit_transcript(self.speculative_transcript)
                                self.speculative_transcript = None
                            elif len(self.speech_buffer) > self.min_speech_duration:
                                # No prefetch available, process normally
                                print(f"{timestamp()} 📝 No prefetch available, processing normally")
                                await self._process_speech_segment(bytes(self.speech_buffer))
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
        self.is_agent_speaking = False
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
        """Set whether agent audio is currently playing"""
        self.is_agent_speaking = speaking
        if speaking:
            print(f"{timestamp()} 🔊 Agent audio playback started")
        else:
            print(f"{timestamp()} 🔇 Agent audio playback stopped")
        
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