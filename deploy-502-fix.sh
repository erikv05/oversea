#!/bin/bash
# Deploy with 502 fix - uses dummy API keys if not set

set -e

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Use existing API keys or dummy values (backend will start even without valid keys)
GEMINI_API_KEY=${GEMINI_API_KEY:-"dummy-key-for-deployment"}
DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY:-"dummy-key-for-deployment"}
ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-"dummy-key-for-deployment"}
ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID:-"21m00Tcm4TlvDq8ikWAM"}

echo "Deploying Voice Agent (502 fix) to project: $PROJECT_ID"
echo ""
echo "Using API Keys:"
echo "  GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "  DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:0:10}..."
echo "  ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY:0:10}..."
echo "  ELEVENLABS_VOICE_ID: $ELEVENLABS_VOICE_ID"
echo ""

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
echo "Test the fix:"
echo "  curl $SERVICE_URL/api/health"
echo ""
echo "Check logs if still getting 502:"
echo "  gcloud run services logs read voice-agent --region us-central1 --limit 50"