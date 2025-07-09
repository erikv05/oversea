#!/usr/bin/env python3
"""Test Deepgram connection and API key"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

async def test_connection():
    """Test Deepgram API key and connection"""
    print("="*60)
    print("Deepgram Connection Test")
    print("="*60)
    
    # Check environment
    api_key = os.getenv("DEEPGRAM_API_KEY")
    
    print(f"\n1. Environment Check:")
    print(f"   - DEEPGRAM_API_KEY present: {'✓ Yes' if api_key else '✗ No'}")
    if api_key:
        print(f"   - Key preview: {api_key[:8]}...{api_key[-4:]}")
        print(f"   - Key length: {len(api_key)} characters")
        
        # Validate key format
        if len(api_key) < 20:
            print(f"   ⚠️  Warning: Key seems too short")
        if not api_key.strip() == api_key:
            print(f"   ⚠️  Warning: Key contains leading/trailing whitespace")
    else:
        print(f"   ✗ Please set DEEPGRAM_API_KEY in your .env file")
        return
    
    print(f"\n2. Testing Deepgram Client Initialization...")
    try:
        from deepgram import DeepgramClient
        client = DeepgramClient(api_key)
        print(f"   ✓ Client created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create client: {type(e).__name__}: {e}")
        return
    
    print(f"\n3. Testing Streaming Connection...")
    try:
        from deepgram import LiveOptions
        
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=8000,
            channels=1
        )
        
        connection = client.listen.asyncwebsocket.v("1")
        
        connected = False
        error_msg = None
        
        def on_open(*args, **kwargs):
            nonlocal connected
            connected = True
            print(f"   ✓ WebSocket opened successfully")
        
        def on_error(*args, **kwargs):
            nonlocal error_msg
            error_msg = kwargs.get("error", "Unknown error")
            print(f"   ✗ WebSocket error: {error_msg}")
        
        def on_close(*args, **kwargs):
            print(f"   - WebSocket closed")
        
        connection.on("open", on_open)
        connection.on("error", on_error)
        connection.on("close", on_close)
        
        print(f"   - Attempting to connect...")
        await connection.start(options)
        
        # Wait for connection
        await asyncio.sleep(1)
        
        if connected:
            print(f"   ✓ Streaming API connection successful!")
            await connection.finish()
        else:
            print(f"   ✗ Failed to connect to streaming API")
            if error_msg:
                print(f"   Error: {error_msg}")
        
    except Exception as e:
        print(f"   ✗ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test complete")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_connection())