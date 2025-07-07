#!/usr/bin/env python3
"""Test script to verify backend can start properly"""

import sys
import os

# Add backend to path
sys.path.insert(0, '/app/backend')
os.environ['PYTHONPATH'] = '/app/backend'

print("Testing backend startup...")

try:
    print("\n1. Testing imports...")
    import fastapi
    print(f"✓ FastAPI version: {fastapi.__version__}")
    
    import uvicorn
    print(f"✓ Uvicorn version: {uvicorn.__version__}")
    
    print("\n2. Testing config import...")
    from config import settings
    print(f"✓ Settings loaded")
    print(f"  - GEMINI_API_KEY: {'SET' if settings.GEMINI_API_KEY else 'NOT SET'}")
    print(f"  - DEEPGRAM_API_KEY: {'SET' if settings.DEEPGRAM_API_KEY else 'NOT SET'}")
    print(f"  - ELEVENLABS_API_KEY: {'SET' if settings.ELEVENLABS_API_KEY else 'NOT SET'}")
    print(f"  - CORS_ORIGINS: {settings.CORS_ORIGINS}")
    
    print("\n3. Testing service imports...")
    from services.deepgram_service import DeepgramService
    print("✓ DeepgramService imported")
    
    from services.elevenlabs_service import ElevenLabsService
    print("✓ ElevenLabsService imported")
    
    from services.gemini_service import GeminiService
    print("✓ GeminiService imported")
    
    print("\n4. Testing route imports...")
    from routes import audio, websocket, agents
    print("✓ Routes imported")
    
    print("\n5. Testing main app import...")
    from main import app
    print("✓ Main app imported successfully")
    
    print("\n✅ All imports successful! Backend should be able to start.")
    
except Exception as e:
    print(f"\n❌ Error during import: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)