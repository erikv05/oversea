# WebRTC VAD Implementation

The interruption detection now uses Google's WebRTC Voice Activity Detection for more accurate voice detection.

## What Changed

1. **Energy-based VAD → WebRTC VAD**: The old system used simple energy thresholds which triggered on any loud noise (fridge slamming, etc.). WebRTC VAD uses advanced signal processing specifically designed for human speech detection.

2. **Key Parameters**:
   - VAD Mode: 2 (0-3, where 3 is most aggressive)
   - Frame duration: 30ms (optimal for WebRTC VAD)
   - Speech start: 90ms (3 frames)
   - Speech end: 1000ms of silence as requested

3. **Benefits**:
   - Excellent at filtering out non-speech sounds
   - Battle-tested in WebRTC applications
   - No model downloads required
   - Fast and lightweight
   - Works offline

## How It Works

WebRTC VAD uses:
- Gaussian Mixture Models (GMM) for speech/non-speech classification
- Noise suppression techniques
- Pitch detection
- Energy-based features

The aggressiveness mode 2 provides a good balance between filtering noise and detecting speech reliably.