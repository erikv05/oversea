#!/usr/bin/env python3
"""Test conversation flow with speculative processing"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

async def test():
    print("Testing Conversation Flow")
    print("="*60)
    
    # Test 1: Test system prompts
    print("\n1. Testing Gemini system prompts...")
    from services.gemini_service import generate_gemini_response_stream
    
    # Test with no agent
    print("\n   Default prompt (no agent):")
    response = ""
    async for chunk in generate_gemini_response_stream(
        "What are you?", 
        [], 
        None
    ):
        response += chunk
    print(f"   Response: {response[:100]}...")
    
    # Test with agent config
    print("\n   With agent config:")
    agent = {
        "system_prompt": "You are Alex, a friendly barista.",
        "behavior": "chatty"
    }
    response = ""
    async for chunk in generate_gemini_response_stream(
        "What are you?", 
        [], 
        agent
    ):
        response += chunk
    print(f"   Response: {response[:100]}...")
    
    # Test 2: Test conversation history management
    print("\n\n2. Testing conversation history with speculative transcripts...")
    
    conversation = []
    
    # Simulate speculative transcript
    print("\n   Adding speculative user message...")
    speculative_msg = {"role": "user", "content": "Hello there"}
    temp_conversation = conversation + [speculative_msg]
    print(f"   Temp conversation: {temp_conversation}")
    print(f"   Actual conversation: {conversation}")
    
    # Simulate confirmed transcript that differs
    print("\n   Confirmed transcript differs...")
    confirmed_msg = {"role": "user", "content": "Hi there"}
    conversation.append(confirmed_msg)
    print(f"   Updated conversation: {conversation}")
    
    print("\n" + "="*60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test())