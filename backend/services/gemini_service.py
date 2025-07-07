"""Google Gemini AI service integration"""
import time
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.helpers import timestamp

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"✓ Gemini API Key configured")
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    print("✗ Warning: GEMINI_API_KEY not found in environment variables")
    model = None


async def generate_gemini_response_stream(user_message: str, conversation: list):
    """Generate streaming response using Google Gemini API"""
    if not model:
        yield "I'm sorry, but the AI model is not configured. Please check your API keys."
        return
    
    try:
        start_time = time.time()
        
        # Simplified prompt for speed
        prompt = "You are a conversational voice assistant. Be concise and natural.\n\n"
        
        # Minimal conversation history (last 4 messages for speed)
        for msg in conversation[-4:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        
        prompt += f"User: {user_message}\nAssistant:"
        
        print(f"{timestamp()} 🤖 LLM: Generating response for '{user_message}'")
        
        # Generate streaming response
        response = model.generate_content(prompt, stream=True)
        
        first_token_time = None
        buffer = ""
        char_count = 0
        
        for chunk in response:
            if chunk.text:
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                    print(f"{timestamp()} ✓ LLM: First token in {first_token_time:.2f}s")
                    
                    # Clean up any "Assistant:" prefix from first chunk
                    cleaned_text = chunk.text
                    if cleaned_text.strip().lower().startswith("assistant:"):
                        cleaned_text = cleaned_text[cleaned_text.lower().find("assistant:") + 10:].lstrip()
                    
                    buffer += cleaned_text
                    char_count += len(cleaned_text)
                    yield cleaned_text
                else:
                    buffer += chunk.text
                    char_count += len(chunk.text)
                    yield chunk.text
        
        total_time = time.time() - start_time
        print(f"{timestamp()} ✓ LLM: Complete ({char_count} chars in {total_time:.2f}s)")
                
    except Exception as e:
        print(f"{timestamp()} ❌ LLM error: {str(e)}")
        yield "I'm sorry, I encountered an error while processing your request."