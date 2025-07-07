#!/usr/bin/env python3
import sys
import os

print(f"Python: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

try:
    print("Importing uvicorn...")
    import uvicorn
    print("✓ Uvicorn imported")
    
    print("Importing main_fixed...")
    from main_fixed import app
    print("✓ Main app imported")
    
    print("Starting server on 0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    
    # Start simple fallback server
    print("\nStarting fallback server...")
    from simple_test import Handler
    from http.server import HTTPServer
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    server.serve_forever()