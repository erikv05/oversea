#!/usr/bin/env python3
"""Start the FastAPI server with better error handling"""

import sys
import os

# Ensure we're in the right directory
os.chdir('/app/backend')
sys.path.insert(0, '/app/backend')

print(f"Starting server from: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    # Direct uvicorn start
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", access_log=True)
except Exception as e:
    print(f"Failed to start server: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)