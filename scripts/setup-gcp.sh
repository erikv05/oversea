#!/bin/bash

# GCP Voice Agent Setup Script
# This script sets up the GCP infrastructure for the voice agent application

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION="us-central1"
ZONE="us-central1-a"
CLUSTER_NAME="voice-cluster"
STATIC_IP_NAME="voice-ip"

echo "Setting up GCP infrastructure for Voice Agent..."
echo "Project ID: $PROJECT_ID"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Create GKE cluster
echo "Creating GKE cluster..."
gcloud container clusters create $CLUSTER_NAME \
  --zone $ZONE \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10 \
  --enable-autorepair \
  --enable-autoupgrade

# Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone $ZONE

# Reserve static IP
echo "Reserving static IP address..."
gcloud compute addresses create $STATIC_IP_NAME --global

# Get the reserved IP
STATIC_IP=$(gcloud compute addresses describe $STATIC_IP_NAME --global --format="get(address)")
echo "Reserved IP: $STATIC_IP"

# Create namespace
echo "Creating Kubernetes namespace..."
kubectl apply -f k8s/namespace.yaml

# Deploy applications
echo "Deploying applications..."
# First update the PROJECT_ID in deployment files
sed -i "s/PROJECT_ID/$PROJECT_ID/g" k8s/backend-deployment.yaml
sed -i "s/PROJECT_ID/$PROJECT_ID/g" k8s/frontend-deployment.yaml

kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your DNS to point voice.addojo.ai to $STATIC_IP"
echo "2. Create k8s/secrets.yaml from k8s/secrets-template.yaml with your actual secrets"
echo "3. Apply secrets: kubectl apply -f k8s/secrets.yaml"
echo "4. Wait for SSL certificate to be provisioned (can take up to 15 minutes)"
echo "5. Access your application at https://voice.addojo.ai"