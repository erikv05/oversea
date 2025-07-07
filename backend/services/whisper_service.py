"""OpenAI Whisper service integration"""
import io
import time
import wave
from typing import Optional
from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY, WHISPER_MODEL
from utils.helpers import timestamp

# Configure OpenAI Whisper
if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    print(f"✓ OpenAI client initialized (model: {WHISPER_MODEL})")
else:
    print("✗ Warning: OPENAI_API_KEY not found")
    openai_client = None


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
    """Transcribe audio with Whisper"""
    if not openai_client:
        print(f"{timestamp()} ❌ Whisper error: OpenAI client not configured")
        return None
        
    try:
        transcribe_start = time.time()
        print(f"{timestamp()} 🎯 Starting Whisper transcription")
        
        # Trust WebRTC VAD - no additional energy checks
        # WebRTC VAD has already determined this is speech
        
        # Convert to WAV
        print(f"{timestamp()} 🎯 Converting to WAV format")
        wav_data = convert_to_wav(audio_data)
        
        # Create file-like object
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "audio.wav"
        
        audio_duration = len(audio_data)/16000
        print(f"{timestamp()} 🎯 Sending {audio_duration:.1f}s audio to OpenAI API")
        api_start = time.time()
        
        # Transcribe with Whisper
        transcript = await openai_client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            # Use empty prompt to reduce hallucinations
            prompt=""
        )
        
        api_time = time.time() - api_start
        print(f"{timestamp()} 🎯 OpenAI API responded ({api_time:.3f}s)")
        
        transcript_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
        
        # Check for hallucinations
        hallucination_patterns = [
            "www.", ".com", ".gov", ".org",
            "transcription by", "translation by", 
            "for more information visit",
            "thank you for watching",
            "accurate transcription of spoken words",
            "transcribe spoken words",
            "real-time conversation transcription"
        ]
        
        # Also check if it's just the prompt being repeated
        is_hallucination = (
            any(pattern.lower() in transcript_text.lower() for pattern in hallucination_patterns) or
            transcript_text.lower().strip() == "accurate transcription of spoken words." or
            len(transcript_text.strip()) < 3  # Too short to be real speech
        )
        
        if is_hallucination:
            print(f"{timestamp()} ⚠️  Whisper: Rejected hallucination: '{transcript_text}'")
            return None
        
        total_time = time.time() - transcribe_start
        print(f"{timestamp()} 🎯 Transcription complete: '{transcript_text[:50]}...' (total: {total_time:.3f}s)")
        
        return transcript_text.strip()
        
    except Exception as e:
        print(f"{timestamp()} ❌ Whisper error: {e}")
        return None