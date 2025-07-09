#!/bin/bash
# Start server with SSL certificates configured

echo "Starting Voice Agent Server with SSL fix..."

# Set SSL certificate environment variables
export SSL_CERT_FILE=$(python3 -m certifi)
export REQUESTS_CA_BUNDLE=$(python3 -m certifi)

echo "SSL_CERT_FILE set to: $SSL_CERT_FILE"

# Start the server
python3 main.py