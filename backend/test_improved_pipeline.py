#!/usr/bin/env python3
"""Test the improved pipeline with speculative processing"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

async def test():
    print("Testing Improved Pipeline")
    print("="*60)
    
    # Test 1: Test interim transcript callback
    print("\n1. Testing DeepgramStreamingTranscriber with interim callback...")
    
    from services.deepgram_service import DeepgramStreamingTranscriber
    from utils.helpers import timestamp
    
    interim_transcripts = []
    final_transcripts = []
    
    def on_transcript(text):
        final_transcripts.append(text)
        print(f"{timestamp()} Final: '{text}'")
    
    def on_interim(text):
        interim_transcripts.append(text)
        print(f"{timestamp()} Interim: '{text}'")
    
    transcriber = DeepgramStreamingTranscriber(
        on_transcript=on_transcript,
        on_interim=on_interim
    )
    
    connected = await transcriber.connect()
    if connected:
        print("   ✓ Connected with interim callback")
        
        # Test get_current_transcript
        current = transcriber.get_current_transcript()
        print(f"   Current transcript: '{current}'")
        
        await transcriber.disconnect()
    else:
        print("   ✗ Failed to connect")
    
    # Test 2: Test speculative processing simulation
    print("\n2. Testing speculative processing flow...")
    
    # Simulate transcript queue
    transcript_queue = asyncio.Queue()
    
    # Add speculative transcript
    await transcript_queue.put({
        "text": "hello world",
        "speculative": True,
        "timestamp": 1234567890
    })
    
    # Get and verify
    item = await transcript_queue.get()
    print(f"   Speculative transcript: '{item['text']}' (speculative={item['speculative']})")
    
    # Add confirmed transcript that matches
    await transcript_queue.put({
        "text": "hello world",
        "speculative": False,
        "confirmed": True,
        "timestamp": 1234567891
    })
    
    item = await transcript_queue.get()
    print(f"   Confirmed transcript: '{item['text']}' (confirmed={item.get('confirmed', False)})")
    
    # Add confirmed transcript that differs
    await transcript_queue.put({
        "text": "goodbye world",
        "speculative": False,
        "cancelled_speculation": True,
        "timestamp": 1234567892
    })
    
    item = await transcript_queue.get()
    print(f"   Different transcript: '{item['text']}' (cancelled={item.get('cancelled_speculation', False)})")
    
    print("\n" + "="*60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test())