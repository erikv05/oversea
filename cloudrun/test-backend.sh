#!/bin/bash
# Test script to check if backend starts correctly

cd /app/backend
export PYTHONPATH=/app/backend

# Test imports
python -c "
import sys
print('Python path:', sys.path)
print('Testing imports...')
from main import app
print('✓ Main app imported successfully')
from routes.agents import router
print('✓ Agents router imported successfully')
print('All imports successful!')
"