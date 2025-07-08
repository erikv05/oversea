import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.main import app

# Vercel expects a variable named 'app'
handler = app