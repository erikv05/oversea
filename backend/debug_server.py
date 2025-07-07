#!/usr/bin/env python3
"""Debug server startup"""

import sys
import os

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Working directory:", os.getcwd())
print("PYTHONPATH:", os.environ.get('PYTHONPATH'))

# Try minimal imports
try:
    print("\nTrying imports...")
    import fastapi
    print("✓ FastAPI imported")
    
    import uvicorn
    print("✓ Uvicorn imported")
    
    # Try to start a minimal server
    from fastapi import FastAPI
    
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Debug server running"}
    
    @app.get("/api/debug")
    def debug():
        return {
            "working_dir": os.getcwd(),
            "python_path": sys.path,
            "env_vars": {
                "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
                "DEEPGRAM_API_KEY": bool(os.getenv("DEEPGRAM_API_KEY")),
                "ELEVENLABS_API_KEY": bool(os.getenv("ELEVENLABS_API_KEY")),
            }
        }
    
    print("\nStarting debug server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    
except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)