"""Deepgram speech-to-text service integration - Streaming only"""
import asyncio
import time
import ssl
import os
from typing import Callable
from deepgram import DeepgramClient, DeepgramClientOptions, LiveOptions, LiveResultResponse, LiveTranscriptionEvents
from config.settings import DEEPGRAM_API_KEY
from utils.helpers import timestamp

# Fix SSL certificate issues on macOS
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    print(f"✓ SSL certificates configured: {certifi.where()}")
except ImportError:
    print("⚠️  certifi not installed - SSL verification may fail")
    print("  Run: pip install certifi")

# Configure Deepgram client
if DEEPGRAM_API_KEY:
    try:
        # Initialize with API key and keepalive option
        config = DeepgramClientOptions(options={"keepalive": "true"})
        deepgram_client = DeepgramClient(DEEPGRAM_API_KEY, config=config)
        print(f"✓ Deepgram client initialized")
        print(f"  API Key: {DEEPGRAM_API_KEY[:8]}...{DEEPGRAM_API_KEY[-4:]}")
        print(f"  Key length: {len(DEEPGRAM_API_KEY)} characters")
    except Exception as e:
        print(f"✗ Warning: Failed to initialize Deepgram client: {e}")
        print(f"  Error type: {type(e).__name__}")
        deepgram_client = None
else:
    print("✗ Warning: DEEPGRAM_API_KEY not found in environment")
    print("  Please set DEEPGRAM_API_KEY in your .env file")
    deepgram_client = None


class DeepgramStreamingTranscriber:
    """Handle streaming transcription with Deepgram"""
    
    def __init__(self, on_transcript: Callable[[str], None]):
        self.on_transcript = on_transcript
        self.connection = None
        self.is_connected = False
        self.transcript_buffer = ""
        self.keep_alive_task = None
        
    async def connect(self):
        """Connect to Deepgram streaming API"""
        if not deepgram_client:
            print(f"{timestamp()} ❌ Deepgram streaming error: Client not configured")
            if not DEEPGRAM_API_KEY:
                print(f"{timestamp()} ❌ DEEPGRAM_API_KEY is not set in environment")
            return False
            
        try:
            print(f"{timestamp()} 🔗 Connecting to Deepgram streaming API...")
            print(f"{timestamp()} 📊 Connection details:")
            print(f"     • API Key present: {'Yes' if DEEPGRAM_API_KEY else 'No'}")
            if DEEPGRAM_API_KEY:
                print(f"     • Key preview: {DEEPGRAM_API_KEY[:8]}...{DEEPGRAM_API_KEY[-4:]}")
                print(f"     • Key length: {len(DEEPGRAM_API_KEY)} chars")
            
            # Configure streaming options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                punctuate=True,
                smart_format=True,
                encoding="linear16",
                sample_rate=8000,
                channels=1,
                endpointing=False,  # We handle our own endpointing with VAD
                interim_results=True,  # Get partial results for lower latency
                utterance_end_ms=1000,  # Only for safety, we manage this with VAD
                vad_events=False,  # We use our own VAD
            )
            
            print(f"{timestamp()} 📋 Streaming options:")
            print(f"     • Model: nova-2")
            print(f"     • Sample rate: 8000 Hz")
            print(f"     • Encoding: linear16")
            
            # Create websocket connection
            print(f"{timestamp()} 🔌 Creating WebSocket connection...")
            try:
                self.connection = deepgram_client.listen.asyncwebsocket.v("1")
            except Exception as e:
                print(f"{timestamp()} ❌ Failed to create connection object: {type(e).__name__}: {e}")
                raise
            
            # Set up event handlers
            print(f"{timestamp()} 📡 Setting up event handlers...")
            self.connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.connection.on(LiveTranscriptionEvents.Close, self._on_close)
            self.connection.on(LiveTranscriptionEvents.Error, self._on_error)
            
            # Start the connection
            print(f"{timestamp()} 🚀 Starting connection...")
            try:
                await self.connection.start(options)
            except Exception as e:
                print(f"{timestamp()} ❌ Failed to start connection: {type(e).__name__}: {e}")
                if hasattr(e, 'response'):
                    print(f"{timestamp()} 📋 Response: {e.response}")
                if hasattr(e, 'status_code'):
                    print(f"{timestamp()} 📋 Status code: {e.status_code}")
                raise
            
            # Wait for connection to be established
            max_wait = 2.0  # Maximum 2 seconds to wait
            wait_time = 0.0
            while not self.is_connected and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            # Send initial audio immediately to prevent timeout
            if self.is_connected:
                print(f"{timestamp()} 🎵 Sending initial audio to establish connection")
                try:
                    # Generate 200ms of silence (8000 Hz, 16-bit, mono = 3200 bytes)
                    silence = b'\x00\x00' * 1600  # 3200 bytes of silence
                    await self.connection.send(silence)
                    print(f"{timestamp()} ✅ Initial audio sent successfully")
                except Exception as e:
                    print(f"{timestamp()} ⚠️  Initial audio failed: {e}")
                    self.is_connected = False
            
            # Final connection check
            if self.is_connected:
                print(f"{timestamp()} ✅ Successfully connected to Deepgram streaming")
            else:
                print(f"{timestamp()} ❌ Failed to establish connection (is_connected={self.is_connected})")
            
            return self.is_connected
            
        except Exception as e:
            print(f"{timestamp()} ❌ Deepgram streaming connection error: {type(e).__name__}: {e}")
            print(f"{timestamp()} 📋 Full error details:")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_audio(self, audio_chunk: bytes):
        """Send audio chunk to Deepgram"""
        if self.connection and self.is_connected:
            try:
                await self.connection.send(audio_chunk)
            except Exception as e:
                print(f"{timestamp()} ❌ Error sending audio to Deepgram: {e}")
    
    async def finalize(self) -> str:
        """Finalize the current utterance and get the final transcript"""
        if self.connection and self.is_connected:
            try:
                # The SDK v4+ uses finalize() method instead of sending a message
                await self.connection.finalize()
                # Wait a bit for final results
                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"{timestamp()} ❌ Error finalizing transcript: {e}")
        
        # Return accumulated transcript
        final_transcript = self.transcript_buffer.strip()
        self.transcript_buffer = ""
        return final_transcript
    
    async def disconnect(self):
        """Disconnect from Deepgram"""
        self.is_connected = False
        
        # Cancel keep-alive task
        if self.keep_alive_task and not self.keep_alive_task.done():
            self.keep_alive_task.cancel()
            
        if self.connection:
            try:
                await self.connection.finish()
            except Exception as e:
                print(f"{timestamp()} ❌ Error disconnecting from Deepgram: {e}")
            finally:
                self.connection = None
    
    async def _on_open(self, client, open, **kwargs):
        """Handle connection open event"""
        print(f"{timestamp()} ✅ Deepgram streaming connection established")
        self.is_connected = True
        # Start keep-alive task
        self.keep_alive_task = asyncio.create_task(self._keep_alive())
    
    async def _on_transcript(self, client, result, **kwargs):
        """Handle transcript event"""
        if result and isinstance(result, LiveResultResponse):
            transcript = result.channel.alternatives[0].transcript
            
            if result.is_final:
                # Final transcript for this segment
                if transcript:
                    print(f"{timestamp()} 📝 Deepgram final: '{transcript}'")
                    self.transcript_buffer += transcript + " "
                    # Callback with the partial transcript
                    if self.on_transcript:
                        self.on_transcript(transcript)
            else:
                # Interim results for lower latency feedback
                if transcript:
                    print(f"{timestamp()} 📝 Deepgram interim: '{transcript}'")
    
    async def _on_close(self, client, close, **kwargs):
        """Handle connection close event"""
        print(f"{timestamp()} 🔌 Deepgram streaming connection closed")
        self.is_connected = False
        # Cancel keep-alive task
        if self.keep_alive_task and not self.keep_alive_task.done():
            self.keep_alive_task.cancel()
    
    async def _on_error(self, client, error, **kwargs):
        """Handle error event"""
        print(f"{timestamp()} ❌ Deepgram streaming error: {error}")
        print(f"{timestamp()} 📋 Error details: {kwargs}")
    
    async def _keep_alive(self):
        """Send periodic audio to prevent timeout"""
        while self.is_connected:
            try:
                # Send audio every 8 seconds (Deepgram timeout is 10s)
                await asyncio.sleep(8)
                if self.is_connected and self.connection:
                    # Send silent audio to keep connection alive
                    # 100ms of silence at 8000 Hz
                    silence = b'\x00\x00' * 800
                    await self.connection.send(silence)
            except Exception as e:
                print(f"{timestamp()} ⚠️  Keep-alive error: {e}")
                break


