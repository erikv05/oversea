# Simple Cloud Run Deployment

This is the simplest way to deploy your Voice Agent to Google Cloud Platform.

## Prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Have a Google Cloud account with billing enabled
3. Have your API keys ready:
   - GEMINI_API_KEY
   - DEEPGRAM_API_KEY  
   - ELEVENLABS_API_KEY
   - ELEVENLABS_VOICE_ID

## Quick Deploy (5 minutes)

### 1. Set up your environment

```bash
# Set your API keys as environment variables
export GEMINI_API_KEY="your-gemini-key"
export DEEPGRAM_API_KEY="your-deepgram-key"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
export ELEVENLABS_VOICE_ID="your-voice-id"
```

### 2. Login to Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Enable required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 4. Deploy the application

```bash
./deploy-cloudrun.sh YOUR_PROJECT_ID
```

This will:
- Build a combined Docker image
- Push it to Google Container Registry
- Deploy to Cloud Run
- Give you a URL like: https://voice-agent-abc123-uc.a.run.app

### 5. Set up custom domain (optional)

In Google Cloud Console:

1. Go to **Cloud Run** > Select your service
2. Click **Manage Custom Domains**
3. Click **Add Mapping**
4. Select **Register a new domain** or use existing
5. Enter `voice.addojo.ai`
6. Follow the DNS instructions provided

## Testing

Once deployed, visit your Cloud Run URL or custom domain and test the voice agent.

## Updating

To update after making changes:

```bash
./deploy-cloudrun.sh YOUR_PROJECT_ID
```

## Costs

With 1-2 concurrent users:
- **Estimated monthly cost**: $0-5
- Cloud Run charges only for actual usage
- Free tier includes 2 million requests/month

## Troubleshooting

### Check logs
```bash
gcloud run services logs read voice-agent --region us-central1
```

### Common issues

1. **WebSocket not connecting**: Make sure your browser allows microphone access over HTTPS
2. **No audio**: Check ELEVENLABS_API_KEY and VOICE_ID are correct
3. **No speech recognition**: Verify DEEPGRAM_API_KEY is valid

## Environment Variables

You can update environment variables anytime:

```bash
gcloud run services update voice-agent \
  --update-env-vars KEY=value \
  --region us-central1
```

## That's it!

Your voice agent is now live. No Kubernetes, no complex configs - just Cloud Run.