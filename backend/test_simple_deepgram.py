#!/usr/bin/env python3
"""Simple test of Deepgram SDK"""
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    
    if not api_key:
        print("No API key found!")
        return
        
    print(f"Key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        from deepgram import DeepgramClient, LiveOptions
        
        # Test 1: Create client
        print("\n1. Creating client...")
        dg = DeepgramClient(api_key)
        print("   ✓ Client created")
        
        # Test 2: Create connection
        print("\n2. Creating connection...")
        connection = dg.listen.asyncwebsocket.v("1")
        print("   ✓ Connection object created")
        
        # Test 3: Start connection
        print("\n3. Starting connection...")
        
        connected = False
        
        def on_open(*args):
            nonlocal connected
            connected = True
            print("   ✓ Connected!")
            
        def on_error(*args, **kwargs):
            print(f"   ✗ Error: {kwargs}")
            
        connection.on("open", on_open)
        connection.on("error", on_error)
        
        options = LiveOptions(
            model="nova-2",
            language="en-US"
        )
        
        await connection.start(options)
        await asyncio.sleep(1)
        
        if connected:
            print("   ✓ Successfully connected to Deepgram!")
            await connection.finish()
        else:
            print("   ✗ Failed to connect")
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())