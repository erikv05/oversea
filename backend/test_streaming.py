#!/usr/bin/env python3
"""Test script for Deepgram streaming API integration"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from services.deepgram_service import DeepgramStreamingTranscriber
from utils.helpers import timestamp


async def test_streaming():
    """Test the streaming transcription"""
    print(f"{timestamp()} 🧪 Testing Deepgram streaming API...")
    
    # Track transcripts
    transcripts = []
    
    def on_transcript(text):
        """Handle transcript updates"""
        print(f"{timestamp()} 📝 Received transcript: '{text}'")
        transcripts.append(text)
    
    # Create transcriber
    transcriber = DeepgramStreamingTranscriber(on_transcript)
    
    # Connect
    connected = await transcriber.connect()
    if not connected:
        print(f"{timestamp()} ❌ Failed to connect to Deepgram")
        return
    
    print(f"{timestamp()} ✅ Connected! Simulating audio stream...")
    
    # Simulate sending audio chunks (you would send real audio here)
    # For now, just test the connection
    await asyncio.sleep(1)
    
    # Finalize and get result
    final = await transcriber.finalize()
    print(f"{timestamp()} 🎯 Final transcript: '{final}'")
    
    # Disconnect
    await transcriber.disconnect()
    print(f"{timestamp()} ✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_streaming())