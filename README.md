# Voice Agent Platform

A real-time voice agent platform using Google Cloud Speech-to-Text, Gemini Pro, and ElevenLabs TTS.

## Features

- 🎤 Professional speech recognition using Google Cloud Speech-to-Text
- 🎙️ Real-time audio streaming from browser to backend
- 🤖 AI responses powered by Google Gemini 2.0 Flash
- 🔊 Natural text-to-speech with ElevenLabs
- 🔄 WebSocket-based real-time communication
- ⚡ Low-latency voice conversations
- 🎯 Instant interruption when user speaks
- 💬 Conversation history tracking

## Setup

### Prerequisites

- Node.js 20+ and npm
- Python 3.8+
- Google Cloud service account with Speech-to-Text API enabled
- Google Gemini API key
- ElevenLabs API key (optional, for TTS)

### Installation

1. Clone the repository and install dependencies:

```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cd backend
cp .env.example .env
# Edit .env and add:
# - GOOGLE_APPLICATION_CREDENTIALS: Path to your Google Cloud service account JSON
# - GEMINI_API_KEY: Your Gemini API key
# - ELEVENLABS_API_KEY: (Optional) Your ElevenLabs API key
```

3. Run the application:

```bash
# From the root directory
npm install
npm run dev
```

This will start:
- Frontend at http://localhost:5173
- Backend at http://localhost:8000

## Usage

1. Click the phone button to start a call
2. Speak naturally - your speech is streamed to Google Cloud STT
3. Complete sentences are sent to Gemini for responses
4. AI responses are spoken back using ElevenLabs TTS
5. Interrupt anytime by speaking - the AI stops immediately

## Technical Details

### Audio Processing
- Browser captures microphone audio at 48kHz
- Audio is downsampled to 8kHz mono for optimal STT performance
- Streams as LINEAR16 PCM chunks via WebSocket
- Google Cloud STT provides real-time transcription with automatic punctuation

### Response Generation
- Complete sentences (ending with `.`, `?`, or `!`) trigger AI responses
- Gemini generates conversational responses
- Responses are chunked into 1-2 sentence segments for natural TTS
- ElevenLabs converts text to speech with low latency

### Interruption Handling
- Interim speech results immediately stop AI audio playback
- All pending audio chunks are cancelled
- New conversation turn begins seamlessly

## API Keys

- **Google Cloud**: Create a service account at https://console.cloud.google.com
  - Enable the Speech-to-Text API
  - Download the service account JSON key
- **Google Gemini**: Get your API key at https://aistudio.google.com/app/apikey
- **ElevenLabs**: Get your API key at https://elevenlabs.io/

## Tech Stack

- **Frontend**: React, TypeScript, Vite, Web Audio API
- **Backend**: FastAPI, WebSockets, Google Cloud STT, Gemini AI, ElevenLabs TTS
- **Audio**: 8kHz LINEAR16 PCM streaming
- **Communication**: WebSocket for bidirectional streaming