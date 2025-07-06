"""ElevenLabs TTS service integration"""
import asyncio
import time
import uuid
from elevenlabs import generate, save, Voice, VoiceSettings
from config.settings import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL, AUDIO_DIR
from utils.helpers import timestamp

# Configure ElevenLabs
if ELEVENLABS_API_KEY:
    print(f"✓ ElevenLabs configured (voice: {ELEVENLABS_VOICE_ID})")
else:
    print("✗ Warning: ELEVENLABS_API_KEY not found")


async def generate_tts_audio_fast(text: str) -> str:
    """Generate TTS audio using ElevenLabs API with optimizations"""
    if not ELEVENLABS_API_KEY:
        return None
    
    try:
        start_time = time.time()
        
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = AUDIO_DIR / f"{audio_id}.mp3"
        
        print(f"{timestamp()} 🔊 TTS: Generating audio for '{text[:50]}...'")
        
        # Use the fastest settings
        voice_settings = VoiceSettings(
            stability=0.5,  # Lower for faster generation
            similarity_boost=0.75
        )
        
        # Run the blocking ElevenLabs API call in a thread pool
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,  # Use default thread pool
            lambda: generate(
                api_key=ELEVENLABS_API_KEY,
                text=text,
                voice=Voice(
                    voice_id=ELEVENLABS_VOICE_ID,
                    settings=voice_settings
                ),
                model=ELEVENLABS_MODEL
            )
        )
        
        # Save audio to file
        await loop.run_in_executor(None, save, audio, str(audio_path))
        
        generation_time = time.time() - start_time
        print(f"{timestamp()} ✓ TTS: Complete in {generation_time:.2f}s")
        
        # Return URL path for the audio file
        return f"/audio/{audio_id}"
        
    except Exception as e:
        print(f"{timestamp()} ❌ TTS error: {str(e)}")
        return None