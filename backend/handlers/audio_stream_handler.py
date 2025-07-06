"""Audio stream handler with Voice Activity Detection"""
import asyncio
import time
from typing import Optional
from fastapi import WebSocket
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
        
        # Voice Activity Detection parameters
        self.speech_buffer = bytearray()  # Buffer for current speech segment
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        
        # Pre-speech circular buffer
        self.pre_speech_buffer_size = VAD_CONFIG["pre_speech_buffer_size"]
        self.pre_speech_buffer = bytearray()
        
        # VAD thresholds
        self.energy_threshold = VAD_CONFIG["energy_threshold"]
        self.speech_start_frames = VAD_CONFIG["speech_start_frames"]
        self.speech_prefetch_frames = VAD_CONFIG["speech_prefetch_frames"]
        self.speech_confirm_frames = VAD_CONFIG["speech_confirm_frames"]
        self.frame_size = VAD_CONFIG["frame_size"]
        
        # Minimum speech duration
        self.min_speech_duration = VAD_CONFIG["min_speech_duration"]
        
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
            
        # Process audio in frames for VAD (10ms frames)
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
                    print(f"{timestamp()} 🎤 Speech started (energy: {frame_energy:.0f}, threshold: {self.energy_threshold})")
                    
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
                    
                    # Start prefetch after 200ms of silence
                    if self.silence_counter == self.speech_prefetch_frames:
                        if len(self.speech_buffer) > self.min_speech_duration and not self.is_speculating:
                            self.is_speculating = True
                            buffer_size_ms = len(self.speech_buffer) / 16
                            print(f"{timestamp()} 🔮 Starting prefetch (200ms silence, {buffer_size_ms:.0f}ms audio)")
                            
                            # Start prefetch task
                            self.speculative_task = asyncio.create_task(
                                self._prefetch_process(bytes(self.speech_buffer))
                            )
                    
                    # Confirm speech ended after 800ms total silence
                    if self.silence_counter >= self.speech_confirm_frames:
                        self.is_speaking = False
                        self.speech_confirmed = True
                        speech_duration = time.time() - self.speech_start_time
                        buffer_size_ms = len(self.speech_buffer) / 16
                        print(f"{timestamp()} ✅ Speech confirmed ended (800ms silence, duration: {speech_duration:.2f}s)")
                        
                        # If we have a prefetched transcript, use it
                        if self.speculative_transcript:
                            print(f"{timestamp()} 🎯 Using prefetched transcript: '{self.speculative_transcript}'")
                            await self._commit_transcript(self.speculative_transcript)
                            self.speculative_transcript = None
                        elif len(self.speech_buffer) > self.min_speech_duration:
                            # No prefetch available, process normally
                            print(f"{timestamp()} 📝 No prefetch available, processing normally")
                            await self._process_speech_segment(bytes(self.speech_buffer))
                        
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
        print(f"{timestamp()} ⏸️  Pausing user speech processing")
        self.is_listening_for_user = False
        
    def resume_listening(self):
        """Resume processing user speech (after agent response)"""
        print(f"{timestamp()} ▶️  Resuming user speech processing")
        self.is_listening_for_user = True
        # Clear any buffered audio and speculative state
        self.speech_buffer.clear()
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        self.speculative_transcript = None
        self.speech_confirmed = False
        self.is_speculating = False
        
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