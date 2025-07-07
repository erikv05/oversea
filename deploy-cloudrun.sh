#!/bin/bash

# Simple Cloud Run deployment script
set -e

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project)}
SERVICE_NAME="voice-agent"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Please provide PROJECT_ID as first argument or set it in gcloud config"
    echo "Usage: ./deploy-cloudrun.sh PROJECT_ID"
    exit 1
fi

echo "Deploying Voice Agent to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"

# Build the image
echo "Building Docker image..."
docker build -f Dockerfile.cloudrun -t $IMAGE_NAME .

# Push to Container Registry
echo "Pushing to Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars="CORS_ORIGINS=https://voice.addojo.ai" \
  --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY" \
  --set-env-vars="DEEPGRAM_API_KEY=$DEEPGRAM_API_KEY" \
  --set-env-vars="ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY" \
  --set-env-vars="ELEVENLABS_VOICE_ID=$ELEVENLABS_VOICE_ID" \
  --set-env-vars="ELEVENLABS_MODEL=eleven_turbo_v2" \
  --set-env-vars="GEMINI_MODEL=gemini-1.5-flash"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Map your custom domain (voice.addojo.ai) to this Cloud Run service"
echo "2. Go to Cloud Run console > $SERVICE_NAME > Manage Custom Domains"
echo "3. Add domain mapping for voice.addojo.ai"
echo "4. Update DNS records as instructed"