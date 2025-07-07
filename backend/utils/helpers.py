"""Helper utilities for the Voice Agent API"""
import time

def timestamp():
    """Return a formatted timestamp for logging"""
    return f"[{time.time():.3f}]"