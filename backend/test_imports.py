#!/usr/bin/env python3
"""Test all imports to identify issues"""

print("Testing imports...")

try:
    print("1. Testing FastAPI import...")
    from fastapi import FastAPI
    print("✓ FastAPI imported")
except Exception as e:
    print(f"✗ FastAPI import failed: {e}")

try:
    print("2. Testing local imports...")
    from config.settings import CORS_ORIGINS
    print("✓ Config imported")
except Exception as e:
    print(f"✗ Config import failed: {e}")

try:
    print("3. Testing routes...")
    from routes.audio import router as audio_router
    print("✓ Audio router imported")
except Exception as e:
    print(f"✗ Audio router import failed: {e}")

try:
    print("4. Testing agents routes...")
    from routes.agents import router as agents_router
    print("✓ Agents router imported")
except Exception as e:
    print(f"✗ Agents router import failed: {e}")

try:
    print("5. Testing websocket...")
    from routes.websocket import websocket_endpoint
    print("✓ WebSocket imported")
except Exception as e:
    print(f"✗ WebSocket import failed: {e}")

print("\nAll import tests complete!")