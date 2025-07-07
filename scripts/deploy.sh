#!/bin/bash

# Deploy script for Voice Agent application
# This script builds and deploys the application to GKE

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
COMMIT_SHA=${2:-$(git rev-parse HEAD)}

echo "Deploying Voice Agent..."
echo "Project ID: $PROJECT_ID"
echo "Commit SHA: $COMMIT_SHA"

# Build and push backend image
echo "Building backend image..."
docker build -t gcr.io/$PROJECT_ID/voice-backend:$COMMIT_SHA ./backend
docker push gcr.io/$PROJECT_ID/voice-backend:$COMMIT_SHA

# Build and push frontend image
echo "Building frontend image..."
docker build -t gcr.io/$PROJECT_ID/voice-frontend:$COMMIT_SHA ./frontend
docker push gcr.io/$PROJECT_ID/voice-frontend:$COMMIT_SHA

# Update deployments
echo "Updating Kubernetes deployments..."
kubectl set image deployment/voice-backend voice-backend=gcr.io/$PROJECT_ID/voice-backend:$COMMIT_SHA -n voice-app
kubectl set image deployment/voice-frontend voice-frontend=gcr.io/$PROJECT_ID/voice-frontend:$COMMIT_SHA -n voice-app

# Wait for rollout
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/voice-backend -n voice-app
kubectl rollout status deployment/voice-frontend -n voice-app

echo "Deployment complete!"
kubectl get pods -n voice-app