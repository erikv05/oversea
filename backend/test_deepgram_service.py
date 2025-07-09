#!/usr/bin/env python3
"""Test the updated DeepgramStreamingTranscriber"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from services.deepgram_service import DeepgramStreamingTranscriber
from utils.helpers import timestamp

async def test():
    print("Testing DeepgramStreamingTranscriber")
    print("="*50)
    
    # Track transcripts
    transcripts = []
    
    def on_transcript(text):
        transcripts.append(text)
        print(f"Received transcript: '{text}'")
    
    # Create transcriber
    transcriber = DeepgramStreamingTranscriber(on_transcript)
    
    # Connect
    print("\n1. Connecting to Deepgram...")
    connected = await transcriber.connect()
    
    if not connected:
        print("   ✗ Failed to connect!")
        return
    
    print("   ✓ Connected successfully!")
    
    # Send some audio
    print("\n2. Sending test audio...")
    
    # Simulate speech (1 second of audio at 8kHz)
    # This is just noise but should trigger the transcription
    for i in range(10):
        # 100ms chunks
        chunk = bytes([i % 256, (i+1) % 256] * 800)  # 1600 bytes = 100ms at 8kHz
        await transcriber.send_audio(chunk)
        await asyncio.sleep(0.1)
    
    print("   ✓ Audio sent")
    
    # Finalize
    print("\n3. Finalizing transcript...")
    final = await transcriber.finalize()
    print(f"   Final transcript: '{final}'")
    
    # Disconnect
    print("\n4. Disconnecting...")
    await transcriber.disconnect()
    print("   ✓ Disconnected")
    
    print("\n" + "="*50)
    print("Test complete!")
    print(f"Received {len(transcripts)} transcript callbacks")

if __name__ == "__main__":
    asyncio.run(test())