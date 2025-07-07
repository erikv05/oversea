#!/bin/bash

# Set environment variables
export PYTHONPATH=/app/backend
export PYTHONUNBUFFERED=1
export CLOUD_RUN=1

# Replace PORT in nginx config
PORT=${PORT:-8080}
sed -i "s/listen 8080/listen $PORT/g" /etc/nginx/sites-available/default

# Log environment for debugging
echo "Starting Voice Agent on Cloud Run"
echo "PORT: $PORT"
echo "PYTHONPATH: $PYTHONPATH"
echo "API Keys configured:"
echo "  GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "  DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:0:10}..."
echo "  ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY:0:10}..."

# Create necessary directories
mkdir -p /app/backend/temp_audio
mkdir -p /app/backend/audio_files

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf