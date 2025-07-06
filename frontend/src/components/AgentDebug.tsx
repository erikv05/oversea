import { useState, useEffect, useRef } from "react";
import { AudioPlayer } from "../AudioPlayer";
import { AudioStreamer } from "../AudioStreamer";

// Timing helper
const timestamp = () => `[${(performance.now() / 1000).toFixed(3)}]`;

function AgentDebug() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [conversation, setConversation] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const conversationRef = useRef<Array<{ role: string; content: string }>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isInitialized = useRef(false);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const currentResponseRef = useRef("");
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const pendingResponseRef = useRef<string | null>(null);
  
  // Performance tracking
  const performanceRef = useRef({
    speechStart: 0,
    speechEnd: 0,
    transcriptReceived: 0,
    streamStart: 0,
    firstTextChunk: 0,
    firstAudioReceived: 0,
    firstAudioPlayed: 0,
  });

  useEffect(() => {
    // Prevent double initialization in development mode
    if (isInitialized.current) {
      console.log(`${timestamp()} Already initialized, skipping...`);
      return;
    }
    isInitialized.current = true;

    // Initialize audio player
    audioPlayerRef.current = new AudioPlayer();
    audioPlayerRef.current.setOnComplete(() => {
      console.log(`${timestamp()} ✓ All audio finished playing`);
      setIsProcessing(false);
      isProcessingRef.current = false;
    });

    // Initialize WebSocket connection
    console.log(`${timestamp()} 🔌 Connecting to WebSocket...`);

    try {
      wsRef.current = new WebSocket("ws://localhost:8000/ws");
    } catch (error) {
      console.error(`${timestamp()} ❌ Failed to create WebSocket:`, error);
      alert("Failed to create WebSocket connection: " + error);
      return;
    }

    wsRef.current.onopen = () => {
      console.log(`${timestamp()} ✓ WebSocket connected`);
    };

    wsRef.current.onerror = (error) => {
      console.error(`${timestamp()} ❌ WebSocket error:`, error);
    };

    wsRef.current.onclose = (event) => {
      console.log(`${timestamp()} 🔌 WebSocket disconnected`, {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
      if (!event.wasClean) {
        setTimeout(() => {
          alert(
            "Failed to connect to the backend. Make sure the server is running on localhost:8000"
          );
        }, 100);
      }
    };

    wsRef.current.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "speech_start":
          console.log(`${timestamp()} 🎤 Speech started`);
          performanceRef.current.speechStart = data.timestamp || performance.now() / 1000;
          break;
          
        case "speech_end":
          console.log(`${timestamp()} 🛑 Speech ended`);
          performanceRef.current.speechEnd = data.timestamp || performance.now() / 1000;
          const speechDuration = performanceRef.current.speechEnd - performanceRef.current.speechStart;
          console.log(`${timestamp()} ⏱️  Speech duration: ${speechDuration.toFixed(2)}s`);
          break;

        case "user_interruption":
          console.log(`${timestamp()} 🗣️  User interruption detected`);
          if (isProcessingRef.current || (audioPlayerRef.current && audioPlayerRef.current.isPlaying())) {
            interruptAI();
            setTranscript(data.text);
          }
          break;

        case "stream_start": {
          performanceRef.current.streamStart = data.timestamp || performance.now() / 1000;
          const transcriptToStream = performanceRef.current.streamStart - performanceRef.current.transcriptReceived;
          console.log(`${timestamp()} 📡 Stream started (${transcriptToStream.toFixed(3)}s after transcript)`);

          // Check if this response is still wanted
          if (!pendingResponseRef.current) {
            console.log(`${timestamp()} ⚠️  Response no longer needed, cancelling`);
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "interrupt" }));
            }
            break;
          }

          // Add user message to conversation
          const userMessage = pendingResponseRef.current;
          setConversation((prev) => {
            const newConv = [
              ...prev,
              { role: "user", content: userMessage },
              { role: "assistant", content: "" },
            ];
            conversationRef.current = newConv;
            return newConv;
          });

          currentResponseRef.current = "";
          setIsProcessing(true);
          isProcessingRef.current = true;
          break;
        }

        case "text_chunk": {
          if (!performanceRef.current.firstTextChunk) {
            performanceRef.current.firstTextChunk = data.timestamp || performance.now() / 1000;
            const timeToFirstToken = performanceRef.current.firstTextChunk - performanceRef.current.speechEnd;
            console.log(`${timestamp()} 📝 First text chunk (${timeToFirstToken.toFixed(3)}s from speech end)`);
          }
          
          // Update the streaming text
          currentResponseRef.current += data.text;
          setConversation((prev) => {
            const newConv = [...prev];
            if (
              newConv.length > 0 &&
              newConv[newConv.length - 1].role === "assistant"
            ) {
              newConv[newConv.length - 1].content = currentResponseRef.current;
            }
            conversationRef.current = newConv;
            return newConv;
          });
          break;
        }

        case "audio_chunk": {
          const audioTimestamp = data.timestamp || performance.now() / 1000;
          if (!performanceRef.current.firstAudioReceived) {
            performanceRef.current.firstAudioReceived = audioTimestamp;
            const timeToFirstAudio = performanceRef.current.firstAudioReceived - performanceRef.current.speechEnd;
            console.log(`${timestamp()} 🔊 First audio received (${timeToFirstAudio.toFixed(3)}s from speech end)`);
            
            // Log complete timing breakdown
            console.log(`${timestamp()} 📊 Timing Breakdown:`);
            console.log(`    • Speech duration: ${(performanceRef.current.speechEnd - performanceRef.current.speechStart).toFixed(2)}s`);
            console.log(`    • Speech → Transcript: ${(performanceRef.current.transcriptReceived - performanceRef.current.speechEnd).toFixed(2)}s`);
            console.log(`    • Transcript → Stream: ${(performanceRef.current.streamStart - performanceRef.current.transcriptReceived).toFixed(2)}s`);
            console.log(`    • Stream → First text: ${(performanceRef.current.firstTextChunk - performanceRef.current.streamStart).toFixed(2)}s`);
            console.log(`    • Speech end → First audio: ${timeToFirstAudio.toFixed(2)}s`);
          }
          
          // Queue audio chunk for playback
          const audioUrl = `http://localhost:8000${data.audio_url}`;
          console.log(`${timestamp()} 🎵 Audio chunk received: "${data.text.substring(0, 30)}..."`);

          if (audioPlayerRef.current) {
            pendingResponseRef.current = null;
            audioPlayerRef.current.addToQueue(audioUrl, data.text);
            
            // Track when first audio actually plays
            if (!performanceRef.current.firstAudioPlayed) {
              setTimeout(() => {
                if (audioPlayerRef.current?.isPlaying()) {
                  performanceRef.current.firstAudioPlayed = performance.now() / 1000;
                  const playDelay = performanceRef.current.firstAudioPlayed - performanceRef.current.firstAudioReceived;
                  console.log(`${timestamp()} 🎧 First audio playing (${playDelay.toFixed(3)}s after received)`);
                }
              }, 50);
            }
          }
          break;
        }

        case "interim_transcript":
          {
            // Show interim transcript
            setTranscript(data.text);
            
            // If AI is speaking and user starts talking, interrupt
            const isAudioPlaying = audioPlayerRef.current?.isPlaying() || false;
            if ((isProcessingRef.current || isAudioPlaying) && data.text.trim().length > 0) {
              console.log(`${timestamp()} 🗣️  User speaking (interim), interrupting AI`);
              interruptAI();
            }
            break;
          }

        case "user_transcript": {
          performanceRef.current.transcriptReceived = data.timestamp || performance.now() / 1000;
          const transcriptionTime = performanceRef.current.transcriptReceived - performanceRef.current.speechEnd;
          console.log(`${timestamp()} 📝 Final transcript: "${data.text}" (${transcriptionTime.toFixed(3)}s after speech end)`);
          
          // Reset performance tracking for next interaction
          performanceRef.current = {
            speechStart: 0,
            speechEnd: 0,
            transcriptReceived: performanceRef.current.transcriptReceived,
            streamStart: 0,
            firstTextChunk: 0,
            firstAudioReceived: 0,
            firstAudioPlayed: 0,
          };
          
          setTranscript("");
          
          // Add to conversation
          const userMessage = data.text;
          setConversation(prev => {
            const newConv = [...prev, { role: "user", content: userMessage }];
            conversationRef.current = newConv;
            return newConv;
          });
          
          // Send to backend for processing
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                type: "message",
                content: userMessage,
                conversation: conversationRef.current,
              })
            );
            pendingResponseRef.current = userMessage;
          }
          break;
        }

        case "stream_complete": {
          const completeTime = data.timestamp || performance.now() / 1000;
          const totalTime = completeTime - performanceRef.current.speechEnd;
          console.log(`${timestamp()} ✅ Stream complete (Total: ${totalTime.toFixed(2)}s from speech end)`);

          // Only update conversation if not interrupted
          if (!data.interrupted) {
            setConversation((prev) => {
              const newConv = [...prev];
              if (
                newConv.length > 0 &&
                newConv[newConv.length - 1].role === "assistant"
              ) {
                newConv[newConv.length - 1].content = data.full_text;
              }
              conversationRef.current = newConv;
              return newConv;
            });
          } else {
            console.log(`${timestamp()} ⚠️  Stream was interrupted`);
            // Remove incomplete messages
            setConversation((prev) => {
              let newConv = [...prev];
              if (
                newConv.length >= 2 &&
                newConv[newConv.length - 1].role === "assistant" &&
                newConv[newConv.length - 2].role === "user"
              ) {
                newConv = newConv.slice(0, -2);
              }
              conversationRef.current = newConv;
              return newConv;
            });
          }

          // Clear pending response
          pendingResponseRef.current = null;

          // Don't set processing to false here - wait for audio to finish
          // The audio player will handle this in its onComplete callback
          break;
        }

        default:
          console.log(`${timestamp()} ❓ Unknown message type:`, data.type);
      }
    };

    return () => {
      console.log(`${timestamp()} 🧹 Cleaning up...`);
      if (audioStreamerRef.current) {
        audioStreamerRef.current.close();
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.stopAll();
      }
    };
  }, []);

  // Start listening function
  const startListening = async () => {
    console.log(`${timestamp()} 🎙️  Starting audio capture...`);
    try {
      // Get microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log(`${timestamp()} ✓ Microphone access granted`);

      // Create audio streamer
      audioStreamerRef.current = new AudioStreamer(stream, wsRef.current!);

      // Send audio config
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log(`${timestamp()} 📤 Sending audio config`);
        wsRef.current.send(
          JSON.stringify({
            type: "audio_config",
            sampleRate: 8000,
            channels: 1,
            format: "pcm16",
          })
        );
      }

      // Start streaming
      audioStreamerRef.current.start();
      setIsListening(true);
      isListeningRef.current = true;
      console.log(`${timestamp()} ✓ Audio streaming started`);
    } catch (error) {
      console.error(`${timestamp()} ❌ Error accessing microphone:`, error);
      alert("Could not access microphone. Please check permissions.");
    }
  };

  // Stop listening function
  const stopListening = () => {
    console.log(`${timestamp()} 🛑 Stopping audio capture`);
    if (audioStreamerRef.current) {
      audioStreamerRef.current.close();
      audioStreamerRef.current = null;
    }
    setIsListening(false);
    isListeningRef.current = false;
  };

  // Function to interrupt the AI
  const interruptAI = () => {
    console.log(`${timestamp()} 🚨 Interrupting AI...`);
    
    // Stop audio playback
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stopAll();
    }

    // Clear current response
    currentResponseRef.current = "";

    // Clear pending response to prevent it from playing
    pendingResponseRef.current = null;

    // Send interrupt signal to backend
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "interrupt" }));
    }

    // Update UI state
    setIsProcessing(false);
    isProcessingRef.current = false;
  };

  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-4xl">
        <h1 className="text-3xl font-bold text-center mb-8">
          Voice Agent (Debug Mode)
        </h1>

        {/* Status indicators */}
        <div className="flex justify-center space-x-4 mb-6">
          <div className={`px-4 py-2 rounded ${isListening ? 'bg-green-500 text-white' : 'bg-gray-300'}`}>
            {isListening ? '🎤 Listening' : '🔇 Not Listening'}
          </div>
          <div className={`px-4 py-2 rounded ${isProcessing ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}>
            {isProcessing ? '🤖 Processing' : '💤 Idle'}
          </div>
        </div>

        {/* Current transcript */}
        {transcript && (
          <div className="mb-6 p-4 bg-yellow-100 rounded">
            <p className="text-sm text-gray-600">Listening...</p>
            <p className="text-lg">{transcript}</p>
          </div>
        )}

        {/* Control button */}
        <div className="flex justify-center mb-8">
          <button
            onClick={toggleListening}
            className={`px-8 py-4 rounded-full font-semibold text-white transition-all ${
              isListening
                ? "bg-red-500 hover:bg-red-600"
                : "bg-blue-500 hover:bg-blue-600"
            }`}
          >
            {isListening ? "Stop Listening" : "Start Listening"}
          </button>
        </div>

        {/* Conversation history */}
        <div className="bg-white rounded-lg shadow-lg p-6 max-h-96 overflow-y-auto">
          <h2 className="text-xl font-semibold mb-4">Conversation</h2>
          {conversation.length === 0 ? (
            <p className="text-gray-500 text-center">
              Start speaking to begin the conversation...
            </p>
          ) : (
            <div className="space-y-4">
              {conversation.map((msg, index) => (
                <div
                  key={index}
                  className={`p-3 rounded ${
                    msg.role === "user"
                      ? "bg-blue-100 ml-auto max-w-[80%]"
                      : "bg-gray-100 mr-auto max-w-[80%]"
                  }`}
                >
                  <p className="font-semibold text-sm mb-1">
                    {msg.role === "user" ? "You" : "Assistant"}
                  </p>
                  <p>{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Debug info */}
        <div className="mt-4 text-xs text-gray-500 text-center">
          <p>Check browser console for detailed timing logs</p>
        </div>
      </div>
    </div>
  );
}

export default AgentDebug;