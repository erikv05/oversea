"""Audio stream handler with Voice Activity Detection"""
import asyncio
import time
from typing import Optional
from fastapi import WebSocket
import webrtcvad
from config.settings import VAD_CONFIG
from services.deepgram_service import DeepgramStreamingTranscriber
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
        # Use mode 3 for maximum aggressiveness in filtering non-speech sounds
        # Combined with our voice detection, this provides robust filtering
        self.vad.set_mode(3)
        
        # Voice Activity Detection parameters
        self.speech_buffer = bytearray()  # Buffer for current speech segment
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0
        
        # Enhanced voice detection for interruption
        self.interruption_speech_counter = 0  # Separate counter for interruption detection
        self.min_interruption_frames = 8  # 240ms of voice-like audio (8 * 30ms) - increased for robustness
        
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
        
        # Streaming transcription
        self.streaming_transcriber = None
        self.is_streaming = False
        
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
                # Enhanced voice detection for interruption
                is_voice_like = self._is_voice_like(frame)
                
                # --- INTERRUPTION DETECTION ---
                if self.is_agent_speaking and not self.is_interrupting:
                    if is_voice_like:
                        # Voice-like audio detected, increment counter
                        self.interruption_speech_counter += 1
                        if self.interruption_speech_counter <= 3:  # Only log first few frames to avoid spam
                            print(f"{timestamp()} 🎤 Voice-like audio detected ({self.interruption_speech_counter}/{self.min_interruption_frames})")
                        
                        # Only interrupt after minimum voice-like duration
                        if self.interruption_speech_counter >= self.min_interruption_frames:
                            self.is_interrupting = True
                            print(f"{timestamp()} 🛑 CONFIRMED voice activity - interrupting agent")
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
                    else:
                        # Not voice-like (could be banging, clicking, etc.), reset counter
                        if self.interruption_speech_counter > 0:
                            print(f"{timestamp()} 🔇 Non-voice audio detected (banging/clicking?) - resetting interruption counter")
                        self.interruption_speech_counter = 0
                elif self.is_agent_speaking and self.is_interrupting:
                    # Already interrupting, continue processing
                    pass
                elif not self.is_agent_speaking:
                    # Reset interruption counter when agent not speaking
                    self.interruption_speech_counter = 0
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
                    
                    # Start streaming transcription immediately
                    if self.is_listening_for_user:
                        # Start connection first
                        await self._start_streaming_transcription()
                        
                        # Send audio immediately after connection is established
                        if self.streaming_transcriber and self.is_streaming:
                            print(f"{timestamp()} 🎤 Sending initial audio to Deepgram")
                            # Send the pre-speech buffer first
                            if len(self.pre_speech_buffer) > 0:
                                await self.streaming_transcriber.send_audio(bytes(self.pre_speech_buffer))
                            # Send current frame
                            await self.streaming_transcriber.send_audio(frame)
                            # Send any accumulated audio
                            if len(self.speech_buffer) > 0:
                                await self.streaming_transcriber.send_audio(bytes(self.speech_buffer))
                    
                    await self.websocket.send_json({
                        "type": "speech_start",
                        "timestamp": time.time()
                    })
                
                if self.is_speaking:
                    # Add frame to speech buffer
                    self.speech_buffer.extend(frame)
                    
                    # Stream audio to Deepgram in real-time
                    if self.is_streaming and self.streaming_transcriber:
                        await self.streaming_transcriber.send_audio(frame)
            else:
                # Silence detected - reset interruption counter
                if self.interruption_speech_counter > 0:
                    print(f"{timestamp()} 🔇 Silence detected - resetting interruption counter ({self.interruption_speech_counter} frames)")
                self.interruption_speech_counter = 0
                
                self.silence_counter += 1
                self.speech_counter = 0
                
                if self.is_speaking:
                    # Continue adding to buffer during short pauses
                    self.speech_buffer.extend(frame)
                    
                    # With streaming, we don't need the 200ms prefetch anymore
                    # The transcript is already being processed in real-time
                    
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
                            
                            # Finalize streaming transcription
                            if self.is_streaming and self.streaming_transcriber:
                                final_transcript = await self.streaming_transcriber.finalize()
                                await self._stop_streaming_transcription()
                                
                                if final_transcript:
                                    print(f"{timestamp()} 🎯 Final streaming transcript: '{final_transcript}'")
                                    await self._commit_transcript(final_transcript)
                                else:
                                    print(f"{timestamp()} ⚠️  No streaming transcript received")
                                    await self.websocket.send_json({
                                        "type": "error",
                                        "message": "Failed to transcribe audio",
                                        "timestamp": time.time()
                                    })
                            else:
                                # Streaming not active - fail fast
                                print(f"{timestamp()} ❌ Streaming transcription not active - cannot process speech")
                                await self.websocket.send_json({
                                    "type": "error",
                                    "message": "Speech recognition unavailable",
                                    "timestamp": time.time()
                                })
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
    
    def _is_voice_like(self, frame: bytes) -> bool:
        """Enhanced voice detection using frequency analysis and energy patterns"""
        import numpy as np
        
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
            
            # 1. Energy checks - voice should have moderate energy levels
            energy = np.mean(audio_data ** 2)
            if energy < 500:  # Increased minimum threshold to filter out quiet background noise
                return False
            if energy > 50000000:  # Too loud for normal voice
                return False
            
            # 2. Check for reasonable amplitude range (voice is usually not clipping)
            max_amplitude = np.max(np.abs(audio_data))
            if max_amplitude > 28000:  # Close to clipping, likely not voice
                return False
            
            # 3. Zero-crossing rate - voice has moderate ZCR, not too high (like fricatives) or too low (like tones)
            zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
            zcr = zero_crossings / len(audio_data)
            if zcr < 0.02 or zcr > 0.4:  # Voice typically has ZCR between 0.02-0.4
                return False
            
            # 4. Frequency analysis using FFT
            fft = np.fft.rfft(audio_data)
            freqs = np.fft.rfftfreq(len(audio_data), 1/8000)
            magnitude = np.abs(fft)
            
            # Voice frequency bands
            # Fundamental frequency range (85-255Hz for adult voices)
            fundamental = np.sum(magnitude[(freqs >= 85) & (freqs <= 255)])
            # First formant range (300-900Hz)
            formant1 = np.sum(magnitude[(freqs >= 300) & (freqs <= 900)])
            # Second formant range (900-2500Hz)
            formant2 = np.sum(magnitude[(freqs >= 900) & (freqs <= 2500)])
            # Higher formants (2500-3400Hz)
            formant3 = np.sum(magnitude[(freqs >= 2500) & (freqs <= 3400)])
            
            total_energy = np.sum(magnitude)
            if total_energy == 0:
                return False
            
            # Calculate ratios
            voice_energy = fundamental + formant1 + formant2 + formant3
            voice_ratio = voice_energy / total_energy
            
            # Check for too much high-frequency content (clicking, banging)
            high_freq_energy = np.sum(magnitude[freqs > 3400])
            high_freq_ratio = high_freq_energy / total_energy
            
            # Check for too much very low frequency content (rumbling, thumps)
            low_freq_energy = np.sum(magnitude[freqs < 85])
            low_freq_ratio = low_freq_energy / total_energy
            
            # 5. Spectral centroid - voice typically has centroid in mid-range
            spectral_centroid = np.sum(freqs * magnitude) / total_energy if total_energy > 0 else 0
            
            # Voice characteristics:
            # - At least 40% energy in voice frequencies (increased from 30%)
            # - Less than 40% energy in high frequencies (reduced from 60%)
            # - Less than 30% energy in very low frequencies
            # - Spectral centroid between 500-2500 Hz
            is_voice = (voice_ratio > 0.4 and 
                       high_freq_ratio < 0.4 and 
                       low_freq_ratio < 0.3 and
                       500 < spectral_centroid < 2500)
            
            return is_voice
            
        except Exception as e:
            print(f"{timestamp()} ⚠️  Voice detection error: {e}")
            # Fallback - be conservative and assume not voice to avoid false positives
            return False
    
    
    
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
    
    async def _start_streaming_transcription(self):
        """Start streaming transcription with Deepgram"""
        # Skip if already streaming
        if self.is_streaming and self.streaming_transcriber:
            return
            
        try:
            print(f"{timestamp()} 🚀 Starting Deepgram streaming transcription")
            
            # Create new transcriber with callback
            self.streaming_transcriber = DeepgramStreamingTranscriber(
                on_transcript=self._on_streaming_transcript
            )
            
            # Connect to Deepgram
            connected = await self.streaming_transcriber.connect()
            if connected:
                self.is_streaming = True
                print(f"{timestamp()} ✅ Streaming transcription active")
            else:
                print(f"{timestamp()} ❌ Failed to connect to Deepgram streaming API")
                self.streaming_transcriber = None
                self.is_streaming = False
                # Send error to frontend
                await self.websocket.send_json({
                    "type": "error",
                    "message": "Speech recognition unavailable - check Deepgram API key",
                    "timestamp": time.time()
                })
                raise Exception("Failed to connect to Deepgram streaming API")
                
        except Exception as e:
            print(f"{timestamp()} ❌ Error starting streaming transcription: {type(e).__name__}: {e}")
            print(f"{timestamp()} 📋 Please check:")
            print(f"     1. DEEPGRAM_API_KEY is set in .env file")
            print(f"     2. The API key is valid and active")
            print(f"     3. Your account has streaming API access")
            print(f"     4. Network connectivity to api.deepgram.com")
            self.streaming_transcriber = None
            self.is_streaming = False
            # Re-raise to fail fast
            raise
    
    async def _stop_streaming_transcription(self):
        """Stop streaming transcription"""
        if self.streaming_transcriber:
            try:
                await self.streaming_transcriber.disconnect()
            except Exception as e:
                print(f"{timestamp()} ❌ Error stopping streaming transcription: {e}")
            finally:
                self.streaming_transcriber = None
                self.is_streaming = False
    
    def _on_streaming_transcript(self, transcript: str):
        """Handle streaming transcript updates"""
        # This gives us real-time partial results
        # The final transcript will be obtained when we call finalize()
        pass