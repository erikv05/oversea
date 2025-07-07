# Backend Structure

## Directory Layout

```
backend/
├── main.py              # Main FastAPI application
├── config/              # Configuration and settings
│   └── settings.py      # Environment variables and constants
├── handlers/            # Request/stream handlers
│   └── audio_stream_handler.py  # WebSocket audio streaming with VAD
├── routes/              # API routes
│   ├── audio.py         # Audio file serving endpoints
│   └── websocket.py     # WebSocket streaming endpoint
├── services/            # External service integrations
│   ├── gemini_service.py      # Google Gemini LLM
│   ├── whisper_service.py     # OpenAI Whisper STT
│   └── elevenlabs_service.py  # ElevenLabs TTS
├── utils/               # Utility functions
│   ├── helpers.py       # General helper functions
│   └── cleanup.py       # File cleanup tasks
└── mcp_client.py        # MCP client (unchanged)
```

## Key Components

### AudioStreamHandler (`handlers/audio_stream_handler.py`)
- Voice Activity Detection (VAD) with aggressive 200ms/800ms thresholds
- Prefetch/speculative processing for low latency
- Circular pre-speech buffer to capture speech beginnings

### Services
- **Gemini**: Streaming LLM responses with conversation history
- **Whisper**: Audio transcription with hallucination detection
- **ElevenLabs**: Fast TTS generation with optimized settings

### Configuration (`config/settings.py`)
- All environment variables and constants in one place
- VAD parameters easily adjustable
- API keys and model configurations