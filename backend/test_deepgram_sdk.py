#!/usr/bin/env python3
"""Test Deepgram SDK with better error handling"""
import os
import asyncio
import certifi
from dotenv import load_dotenv

# Set SSL certificates
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

load_dotenv()

async def test():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    
    if not api_key:
        print("No API key found!")
        return
        
    print(f"Key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        from deepgram import DeepgramClient, DeepgramClientOptions, LiveOptions, LiveTranscriptionEvents
        
        # Test 1: Create client
        print("\n1. Creating client...")
        config = DeepgramClientOptions(options={"keepalive": "true"})
        dg = DeepgramClient(api_key, config=config)
        print("   ✓ Client created")
        
        # Test 2: Create connection
        print("\n2. Creating connection...")
        connection = dg.listen.asyncwebsocket.v("1")
        print("   ✓ Connection object created")
        
        # Test 3: Setup handlers
        print("\n3. Setting up handlers...")
        
        connected = False
        error_details = None
        
        async def on_open(self, open, **kwargs):
            nonlocal connected
            connected = True
            print("   ✓ WebSocket opened!")
            
        async def on_message(self, result, **kwargs):
            print(f"   📝 Message: {result}")
            
        async def on_metadata(self, metadata, **kwargs):
            print(f"   📊 Metadata: {metadata}")
            
        async def on_error(self, error, **kwargs):
            nonlocal error_details
            error_details = error
            print(f"   ✗ Error: {error}")
            
        async def on_close(self, close, **kwargs):
            print(f"   🔌 Connection closed")
            
        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        connection.on(LiveTranscriptionEvents.Close, on_close)
        
        # Test 4: Start connection
        print("\n4. Starting connection...")
        
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=8000,
            channels=1,
            punctuate=True,
            smart_format=True
        )
        
        # Try to start the connection
        success = await connection.start(options)
        print(f"   Start result: {success}")
        
        # Wait a bit for connection
        await asyncio.sleep(2)
        
        if connected:
            print("\n   ✓ Successfully connected to Deepgram!")
            
            # Send some test audio
            print("\n5. Sending test audio...")
            # Send 100ms of silence
            silence = b'\x00\x00' * 800
            await connection.send(silence)
            print("   ✓ Audio sent")
            
            # Wait for any response
            await asyncio.sleep(1)
            
            # Close connection
            await connection.finish()
            print("   ✓ Connection closed cleanly")
        else:
            print("\n   ✗ Failed to connect")
            if error_details:
                print(f"   Error details: {error_details}")
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())