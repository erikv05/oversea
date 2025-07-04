# Oversea

Oversea is a work-in-progress, LLM-created clone of Play.ai. Play.ai supports live voice agents. Right now, we are trying to get Oversea to listen to user prompts, understand them via stt, send them to Gemini, respond with tts and then repeat this process.

The end goal is to have the voice agent feel like a phone call. As such, responses from LLMs are processed in chunks, and sent to tts in chunks as well. This should enable near-real-time processing speeds.
