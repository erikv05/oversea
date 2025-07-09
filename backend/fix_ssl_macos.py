#!/usr/bin/env python3
"""Fix SSL certificate issues on macOS for Deepgram"""
import os
import ssl
import certifi

print("SSL Certificate Fix for macOS")
print("="*50)

# Method 1: Set environment variables
print("\n1. Setting SSL environment variables...")
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
print(f"   SSL_CERT_FILE = {certifi.where()}")

# Method 2: Check Python SSL
print("\n2. Checking Python SSL configuration...")
print(f"   Default verify paths: {ssl.get_default_verify_paths()}")
print(f"   OpenSSL version: {ssl.OPENSSL_VERSION}")

# Method 3: Test certificate loading
print("\n3. Testing certificate loading...")
try:
    context = ssl.create_default_context()
    context.load_verify_locations(certifi.where())
    print("   ✓ Successfully loaded certificates")
except Exception as e:
    print(f"   ✗ Error loading certificates: {e}")

print("\n" + "="*50)
print("To fix SSL issues, run this before starting your server:")
print(f"export SSL_CERT_FILE={certifi.where()}")
print(f"export REQUESTS_CA_BUNDLE={certifi.where()}")
print("\nOr add these to your .env file:")
print(f"SSL_CERT_FILE={certifi.where()}")
print(f"REQUESTS_CA_BUNDLE={certifi.where()}")