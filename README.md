# Voice Agent Platform

A real-time voice agent platform using React, FastAPI, Google Gemini, and ElevenLabs TTS.

## Features

- 🎤 Real-time speech-to-text using Web Speech API
- 🤖 AI responses powered by Google Gemini 2.0 Flash
- 🔊 Natural text-to-speech with ElevenLabs
- 🔄 WebSocket-based real-time communication
- 💬 Conversation history tracking

## Setup

### Prerequisites

- Node.js 20+ and npm
- Python 3.8+
- Google Gemini API key
- ElevenLabs API key

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
# Edit .env and add your API keys
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

1. Click the microphone button to start speaking
2. The agent will listen to your speech and convert it to text
3. When you stop speaking, it sends your message to Gemini for a response
4. The response is spoken back using ElevenLabs TTS
5. Continue the conversation naturally!

## API Keys

- **Google Gemini**: Get your API key at https://aistudio.google.com/app/apikey
- **ElevenLabs**: Get your API key at https://elevenlabs.io/

## Tech Stack

- **Frontend**: React, TypeScript, Vite, Web Speech API
- **Backend**: FastAPI, WebSockets, Google Gemini AI, ElevenLabs TTS
- **Communication**: WebSocket for real-time bidirectional communication