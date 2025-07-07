#!/bin/bash

echo "Starting local development environment..."

# Kill any existing processes
echo "Stopping any existing processes..."
pkill -f "python.*minimal_with_storage.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Start backend
echo ""
echo "Starting backend server on http://localhost:8000..."
cd backend
python3 minimal_with_storage.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start frontend
echo ""
echo "Starting frontend dev server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Local development environment started!"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend:    http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "python.*minimal_with_storage.py" 2>/dev/null
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