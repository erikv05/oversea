#!/usr/bin/env python3
"""Runner script for combined backend"""
import sys
import os

print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Starting combined backend with WebSocket support...", flush=True)

# Run uvicorn
os.system("python -m uvicorn app_combined:app --host 0.0.0.0 --port 8000 --log-level info")