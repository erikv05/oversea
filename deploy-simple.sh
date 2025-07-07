#!/bin/bash
# Minimal deployment using Cloud Build

set -e

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Building and deploying minimal version to project: $PROJECT_ID"

# Create a temporary Cloud Build config
cat > cloudbuild-temp.yaml <<EOF
steps:
  # Build the image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.cloudrun', '-t', 'gcr.io/$PROJECT_ID/voice-agent', '.']
  
  # Push the image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/voice-agent']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'voice-agent'
      - '--image=gcr.io/$PROJECT_ID/voice-agent'
      - '--platform=managed'
      - '--region=us-central1'
      - '--allow-unauthenticated'
      - '--port=8080'
      - '--memory=1Gi'
EOF

# Submit the build
gcloud builds submit --config=cloudbuild-temp.yaml .

# Clean up
rm cloudbuild-temp.yaml

echo "Done! Test with:"
echo "curl $(gcloud run services describe voice-agent --region us-central1 --format 'value(status.url)')/api/health"