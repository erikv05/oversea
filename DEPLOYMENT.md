# Voice Agent Deployment Guide

This guide walks you through deploying the Voice Agent application to Google Cloud Platform (GCP).

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **kubectl** installed
4. **Docker** installed
5. **Domain** configured (voice.addojo.ai)

## Initial Setup

### 1. Configure GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Run the setup script
./scripts/setup-gcp.sh $PROJECT_ID
```

This script will:
- Enable required GCP APIs
- Create a GKE cluster
- Reserve a static IP address
- Create Kubernetes namespace
- Deploy initial configurations

### 2. Configure DNS

After running the setup script, you'll receive a static IP address. Update your DNS records:

1. Go to your DNS provider
2. Create an A record for `voice.addojo.ai` pointing to the static IP
3. Wait for DNS propagation (usually 5-30 minutes)

### 3. Create Secrets

1. Copy the secrets template:
   ```bash
   cp k8s/secrets-template.yaml k8s/secrets.yaml
   ```

2. Edit `k8s/secrets.yaml` and add your base64-encoded secrets:
   ```bash
   # Encode a secret
   echo -n "your-api-key" | base64
   ```

3. Apply the secrets:
   ```bash
   kubectl apply -f k8s/secrets.yaml
   ```

### 4. Initial Deployment

Deploy the application:
```bash
./scripts/deploy.sh $PROJECT_ID
```

## Environment Variables

The backend requires the following environment variables (stored in Kubernetes secrets):

- `OPENAI_API_KEY` or `GEMINI_API_KEY` - For LLM responses
- `DEEPGRAM_API_KEY` - For speech-to-text
- `ELEVENLABS_API_KEY` - For text-to-speech
- `ELEVENLABS_VOICE_ID` - Voice ID for TTS
- `MCP_URL` - (Optional) MCP server URL

## Continuous Deployment

### GitHub Actions

The repository includes a GitHub Actions workflow for automatic deployment:

1. Add these secrets to your GitHub repository:
   - `GCP_PROJECT_ID` - Your GCP project ID
   - `GCP_SA_KEY` - Service account key JSON (base64 encoded)

2. Push to the `main` branch to trigger deployment

### Manual Deployment

To deploy manually:
```bash
./scripts/deploy.sh $PROJECT_ID
```

## Monitoring

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/voice-backend -n voice-app

# Frontend logs
kubectl logs -f deployment/voice-frontend -n voice-app
```

### Check Status

```bash
# Pod status
kubectl get pods -n voice-app

# Service status
kubectl get services -n voice-app

# Ingress status
kubectl get ingress -n voice-app
```

## Troubleshooting

### SSL Certificate Issues

SSL certificates are automatically provisioned by Google. This can take up to 15 minutes. Check status:
```bash
kubectl describe managedcertificate voice-cert -n voice-app
```

### WebSocket Connection Issues

Ensure that:
1. The ingress is properly configured
2. CORS origins include your domain
3. The backend service is running

### Audio Issues

1. Check browser console for microphone permissions
2. Ensure HTTPS is enabled (required for microphone access)
3. Verify ElevenLabs API key and voice ID

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment voice-backend --replicas=5 -n voice-app

# Scale frontend
kubectl scale deployment voice-frontend --replicas=5 -n voice-app
```

### Auto-scaling

The GKE cluster is configured with auto-scaling (3-10 nodes).

## Security Considerations

1. **Secrets**: Never commit actual secrets to the repository
2. **CORS**: Update CORS_ORIGINS in backend deployment for production
3. **API Keys**: Rotate API keys regularly
4. **HTTPS**: Always use HTTPS in production

## Backup and Recovery

### Database Backup

Currently using in-memory storage. For production:
1. Implement persistent storage (Cloud SQL, Firestore)
2. Set up regular backups

### Application Backup

Docker images are stored in Google Container Registry and tagged with commit SHA.

## Cost Optimization

1. **Node Pool**: Start with n1-standard-2 machines
2. **Replicas**: Adjust based on traffic
3. **Audio Storage**: Consider using Cloud Storage for audio files
4. **CDN**: Use Cloud CDN for static assets

## Next Steps

1. Set up monitoring with Google Cloud Monitoring
2. Configure alerts for downtime
3. Implement persistent storage for agents
4. Set up staging environment
5. Configure CI/CD pipelines