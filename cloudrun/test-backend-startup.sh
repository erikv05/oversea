#!/bin/bash

# Test script to debug backend startup issues

echo "Testing backend startup..."

# Check Python version
echo -e "\n1. Python version:"
python --version

# Check if requirements are installed
echo -e "\n2. Checking key dependencies:"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')" 2>&1
python -c "import uvicorn; print(f'Uvicorn: {uvicorn.__version__}')" 2>&1
python -c "import deepgram; print('Deepgram: OK')" 2>&1
python -c "import google.generativeai; print('Google Generative AI: OK')" 2>&1

# Try to import the main module
echo -e "\n3. Testing main.py import:"
cd /app/backend
python -c "import main; print('Main module imported successfully')" 2>&1

# Try to start the server with more verbose output
echo -e "\n4. Starting server with verbose output:"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug