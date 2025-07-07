"""Audio file serving route"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from config.settings import AUDIO_DIR

router = APIRouter()


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve audio files"""
    # Add .mp3 extension if not present
    if not audio_id.endswith('.mp3'):
        audio_id = f"{audio_id}.mp3"
    
    audio_path = AUDIO_DIR / audio_id
    
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/mpeg")
    else:
        return {"error": "Audio file not found"}