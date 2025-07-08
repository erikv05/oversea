#!/bin/bash

# GCP deployment script for backend WebSocket service

# Set your GCP project ID
PROJECT_ID="addojo-e0df0"
REGION="us-central1"
SERVICE_NAME="oversea-backend"

echo "🚀 Deploying backend to Google Cloud Run..."

# Ensure you're in the backend directory
cd backend

# Submit build to Cloud Build
echo "📦 Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml --project $PROJECT_ID

# Get the service URL
echo "🔍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format 'value(status.url)')

echo "✅ Backend deployed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Update frontend/src/config.ts with the service URL:"
echo "   const GCP_WEBSOCKET_URL = 'wss://${SERVICE_URL#https://}/ws';"
echo ""
echo "2. Set environment variables in Cloud Run:"
echo "   - Go to https://console.cloud.google.com/run"
echo "   - Click on $SERVICE_NAME service"
echo "   - Click 'Edit & Deploy New Revision'"
echo "   - Add your environment variables from backend/.env"
echo ""
echo "3. Redeploy frontend to Vercel:"
echo "   vercel --prod"