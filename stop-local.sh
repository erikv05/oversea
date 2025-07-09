#!/bin/bash

# Stop all Oversea local development servers

echo "🛑 Stopping Oversea servers..."

# Kill backend server (Python/Uvicorn)
pkill -f "uvicorn main:app" 2>/dev/null

# Kill frontend server (Vite)
pkill -f "vite" 2>/dev/null

# Kill any node processes on port 5173
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Kill any python processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "✅ All servers stopped"