#!/bin/bash

echo "Starting full Voice Agent development environment..."

# Check for required environment variables
if [ -z "$GEMINI_API_KEY" ] || [ -z "$DEEPGRAM_API_KEY" ] || [ -z "$ELEVENLABS_API_KEY" ]; then
    echo ""
    echo "⚠️  Missing required API keys!"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export GEMINI_API_KEY='your-key'"
    echo "  export DEEPGRAM_API_KEY='your-key'" 
    echo "  export ELEVENLABS_API_KEY='your-key'"
    echo "  export ELEVENLABS_VOICE_ID='your-voice-id' (optional)"
    echo ""
    echo "You can add these to your ~/.zshrc or ~/.bash_profile"
    exit 1
fi

# Kill any existing processes
echo "Stopping any existing processes..."
pkill -f "python.*main.py" 2>/dev/null
pkill -f "uvicorn.*main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Start full backend
echo ""
echo "Starting full backend server on http://localhost:8000..."
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Start frontend
echo ""
echo "Starting frontend dev server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Full Voice Agent environment started!"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend:    http://localhost:5173"
echo ""
echo "API Keys configured:"
echo "  GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "  DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:0:10}..."
echo "  ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY:0:10}..."
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "python.*main.py" 2>/dev/null
    pkill -f "uvicorn.*main:app" 2>/dev/null
    pkill -f "npm run dev" 2>/dev/null
    echo "Services stopped."
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup INT

# Wait forever
while true; do
    sleep 1
done