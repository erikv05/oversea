"""Deepgram speech-to-text service integration"""
import io
import time
import wave
from typing import Optional
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from config.settings import DEEPGRAM_API_KEY
from utils.helpers import timestamp

# Configure Deepgram client
if DEEPGRAM_API_KEY:
    try:
        # Initialize with API key
        deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
        print(f"✓ Deepgram client initialized (key starts with: {DEEPGRAM_API_KEY[:8]}...)")
    except Exception as e:
        print(f"✗ Warning: Failed to initialize Deepgram client: {e}")
        deepgram_client = None
else:
    print("✗ Warning: DEEPGRAM_API_KEY not found")
    deepgram_client = None


def convert_to_wav(audio_data: bytes) -> bytes:
    """Convert raw PCM audio to WAV format"""
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(8000)  # 8kHz
        wav_file.writeframes(audio_data)
    
    wav_buffer.seek(0)
    return wav_buffer.read()


async def transcribe_audio(audio_data: bytes) -> Optional[str]:
    """Transcribe audio with Deepgram"""
    if not deepgram_client:
        print(f"{timestamp()} ❌ Deepgram error: Client not configured")
        return None
        
    try:
        transcribe_start = time.time()
        print(f"{timestamp()} 🎯 Starting Deepgram transcription")
        
        # Trust WebRTC VAD - no additional energy checks
        # WebRTC VAD has already determined this is speech
        
        # Convert to WAV format
        print(f"{timestamp()} 🎯 Converting to WAV format")
        wav_data = convert_to_wav(audio_data)
        
        audio_duration = len(audio_data)/16000
        print(f"{timestamp()} 🎯 Sending {audio_duration:.1f}s audio to Deepgram API")
        api_start = time.time()
        
        # Configure Deepgram options
        options = PrerecordedOptions(
            model="nova-2",  # Latest and most accurate model
            language="en-US",
            punctuate=True,
            smart_format=True  # Automatic punctuation and capitalization
        )
        
        # Create audio source
        source: FileSource = {
            "buffer": wav_data
        }
        
        # Transcribe with Deepgram
        try:
            response = await deepgram_client.listen.asyncrest.v("1").transcribe_file(
                source, options
            )
            
            api_time = time.time() - api_start
            print(f"{timestamp()} 🎯 Deepgram API responded ({api_time:.3f}s)")
            
            # Print full response for debugging
            print(f"{timestamp()} 📋 Deepgram response: {response}")
            
            # Extract transcript text
            transcript = response.results.channels[0].alternatives[0].transcript
        except Exception as api_error:
            print(f"{timestamp()} ❌ Deepgram API error details: {type(api_error).__name__}: {api_error}")
            print(f"{timestamp()} 📋 Options sent: {options}")
            print(f"{timestamp()} 📋 Audio info: {len(wav_data)} bytes, {audio_duration:.1f}s")
            raise
        
        # Check for empty or very short transcripts
        if not transcript or len(transcript.strip()) < 3:
            print(f"{timestamp()} ⚠️  Deepgram: Too short to be real speech")
            return None
        
        total_time = time.time() - transcribe_start
        print(f"{timestamp()} 🎯 Transcription complete: '{transcript[:50]}...' (total: {total_time:.3f}s)")
        
        return transcript.strip()
        
    except Exception as e:
        print(f"{timestamp()} ❌ Deepgram error: {e}")
        return None