#!/bin/bash

# Simplest deployment using Cloud Build
set -e

# Check if API keys are set
if [ -z "$GEMINI_API_KEY" ] || [ -z "$DEEPGRAM_API_KEY" ] || [ -z "$ELEVENLABS_API_KEY" ] || [ -z "$ELEVENLABS_VOICE_ID" ]; then
    echo "Error: Please set all required environment variables:"
    echo "  export GEMINI_API_KEY='your-key'"
    echo "  export DEEPGRAM_API_KEY='your-key'"
    echo "  export ELEVENLABS_API_KEY='your-key'"
    echo "  export ELEVENLABS_VOICE_ID='your-voice-id'"
    exit 1
fi

echo "Deploying Voice Agent using Cloud Build..."

# Submit build and deploy
gcloud builds submit \
  --config=cloudbuild-simple.yaml \
  --substitutions=_GEMINI_API_KEY="$GEMINI_API_KEY",_DEEPGRAM_API_KEY="$DEEPGRAM_API_KEY",_ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY",_ELEVENLABS_VOICE_ID="$ELEVENLABS_VOICE_ID"

# Get the service URL
echo ""
echo "Getting service URL..."
SERVICE_URL=$(gcloud run services describe voice-agent --region us-central1 --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "To add custom domain:"
echo "1. Go to Cloud Console → Cloud Run → voice-agent"
echo "2. Click 'Manage Custom Domains'"
echo "3. Add voice.addojo.ai"