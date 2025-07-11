#!/bin/bash

# Oversea - Local Development Script
# This script runs the same environment as deployed to GCP/Vercel

echo "🚀 Starting Oversea Local Development Environment..."
echo ""

# Check if backend/.env exists
if [ ! -f backend/.env ]; then
    echo "❌ Error: backend/.env file not found!"
    echo ""
    echo "Please create backend/.env with the following variables:"
    echo "  GEMINI_API_KEY=your-key"
    echo "  OPENAI_API_KEY=your-key"
    echo "  ELEVENLABS_API_KEY=your-key"
    echo "  ELEVENLABS_VOICE_ID=your-voice-id"
    echo "  DEEPGRAM_API_KEY=your-key"
    echo ""
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Start backend server
echo "📦 Starting backend server..."
cd backend
.venv/bin/python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! curl -s http://localhost:8000 > /dev/null; then
    echo "❌ Backend failed to start. Check the logs above."
    exit 1
fi

echo "✅ Backend running at http://localhost:8000"
echo ""

# Start frontend server
echo "🎨 Starting frontend server..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Frontend will be available at http://localhost:5173"
echo ""
echo "🎉 Oversea is running locally!"
echo ""
echo "📝 Logs:"
echo "  - Backend logs will appear above"
echo "  - Frontend logs will appear below"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for both processes
wait