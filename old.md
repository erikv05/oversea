# Oversea

Oversea is a work-in-progress, LLM-created clone of Play.ai. Play.ai supports live voice agents. Right now, we are trying to get Oversea to listen to user prompts, understand them via stt, send them to Gemini, respond with tts and then repeat this process.

The end goal is to have the voice agent feel like a phone call. As such, responses from LLMs are processed in chunks, and sent to tts in chunks as well. This should enable near-real-time processing speeds.

# Isolation

This will be a large, complex infrastructure meant for enterprise-grade scale and security. Keep the base calling functionality (i.e. speech-to-text, LLM integration, and text-to-speech replies) **isolated from the rest of the system**. This way, we can make changes to the voice functionality simply without having to rewrite everything (twilio integration, hosting, load balancing, etc.)
