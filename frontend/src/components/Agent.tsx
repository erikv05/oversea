import { useState, useEffect, useRef } from "react";
import { AudioPlayer } from "../AudioPlayer";
import { AudioStreamer } from "../AudioStreamer";

function Agent() {
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

  useEffect(() => {
    // Prevent double initialization in development mode
    if (isInitialized.current) {
      console.log("Already initialized, skipping...");
      return;
    }
    isInitialized.current = true;

    // Initialize audio player
    audioPlayerRef.current = new AudioPlayer();
    audioPlayerRef.current.setOnComplete(() => {
      console.log("All audio finished playing");
      setIsProcessing(false);
      isProcessingRef.current = false;
    });

    // Initialize WebSocket connection
    console.log("Attempting to connect to WebSocket at ws://localhost:8000/ws");

    try {
      wsRef.current = new WebSocket("ws://localhost:8000/ws");
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      alert("Failed to create WebSocket connection: " + error);
      return;
    }

    wsRef.current.onopen = () => {
      console.log("WebSocket connected successfully");
      console.log("WebSocket readyState:", wsRef.current?.readyState);
    };

    wsRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      console.error("WebSocket readyState:", wsRef.current?.readyState);
      console.error("Error details:", {
        type: error.type,
        target: error.target,
        currentTarget: error.currentTarget,
        eventPhase: error.eventPhase,
      });
    };

    wsRef.current.onclose = (event) => {
      console.log("WebSocket disconnected", {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
      if (!event.wasClean) {
        setTimeout(() => {
          alert(
            "Failed to connect to the backend. Make sure the server is running on localhost:8000\n\nError code: " +
              event.code +
              "\nReason: " +
              (event.reason || "Unknown")
          );
        }, 100);
      }
    };

    wsRef.current.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "user_interruption":
          console.log("Backend detected user interruption:", data.text);
          // Trigger interruption if AI is speaking
          if (isProcessingRef.current || (audioPlayerRef.current && audioPlayerRef.current.isPlaying())) {
            interruptAI();
            // Show the interrupting text
            setTranscript(data.text);
          }
          break;

        case "stream_start": {
          console.log("Stream started");

          // Check if this response is still wanted
          if (!pendingResponseRef.current) {
            console.log("Response no longer needed, user continued speaking");
            // Tell backend to cancel
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "interrupt" }));
            }
            break;
          }

          // Add user message to conversation now that we're sure about it
          const userMessage = pendingResponseRef.current;
          setConversation((prev) => {
            // Check if the last message is already this user message (avoid duplicates)
            if (
              prev.length > 0 &&
              prev[prev.length - 1].role === "user" &&
              prev[prev.length - 1].content === userMessage
            ) {
              const newConv = [...prev, { role: "assistant", content: "" }];
              conversationRef.current = newConv;
              return newConv;
            }
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
          // Queue audio chunk for playback
          const audioUrl = `http://localhost:8000${data.audio_url}`;
          console.log("Received audio chunk:", audioUrl, "Text:", data.text);
          console.log(
            "Current state - pending:",
            pendingResponseRef.current,
            "processing:",
            isProcessingRef.current
          );

          if (audioPlayerRef.current) {
            // Clear pending response once audio starts playing
            pendingResponseRef.current = null;
            audioPlayerRef.current.addToQueue(audioUrl, data.text);
          }
          break;
        }

        case "interim_transcript":
          {
            // Show interim transcript
            console.log("Interim transcript received:", data.text);
            setTranscript(data.text);
            
            // If AI is speaking and user starts talking, interrupt
            const isAudioPlaying = audioPlayerRef.current?.isPlaying() || false;
            if ((isProcessingRef.current || isAudioPlaying) && data.text.trim().length > 0) {
              console.log("User speaking (interim), interrupting AI...");
              interruptAI();
            }
            break;
          }

        case "user_transcript": {
          console.log("User transcript received:", data.text);
          setTranscript("");
          
          // Don't add to conversation here - wait for stream_start
          // Just store it as pending
          const userMessage = data.text;
          pendingResponseRef.current = userMessage;
          
          // Send to backend for processing
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                type: "message",
                content: userMessage,
                conversation: conversationRef.current,
              })
            );
          }
          break;
        }

        case "stream_complete": {
          console.log("Stream complete, full text:", data.full_text);

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
            // Remove both the user message and incomplete assistant message
            setConversation((prev) => {
              const newConv = [...prev];
              // Remove assistant message
              if (
                newConv.length > 0 &&
                newConv[newConv.length - 1].role === "assistant"
              ) {
                newConv.pop();
              }
              // Remove user message if it matches the pending one
              if (
                newConv.length > 0 &&
                newConv[newConv.length - 1].role === "user" &&
                newConv[newConv.length - 1].content ===
                  pendingResponseRef.current
              ) {
                newConv.pop();
              }
              conversationRef.current = newConv;
              return newConv;
            });
          }

          // Reset processing state when stream completes
          pendingResponseRef.current = null;
          if (!audioPlayerRef.current || !audioPlayerRef.current.isPlaying()) {
            setIsProcessing(false);
            isProcessingRef.current = false;
          }
          break;
        }
      }
    };

    // No browser speech recognition - using Google Cloud STT via backend

    return () => {
      console.log("Cleanup function called");
      const ws = wsRef.current;
      const audioStreamer = audioStreamerRef.current;
      
      if (ws && ws.readyState === WebSocket.OPEN) {
        console.log("Closing WebSocket in cleanup");
        ws.close();
      }
      if (audioStreamer) {
        audioStreamer.stop();
      }
      isInitialized.current = false;
    };
  }, []);

  const startListening = async () => {
    if (audioStreamerRef.current) {
      try {
        audioStreamerRef.current.start();
        setTranscript("");
        console.log("Audio streaming started successfully");
      } catch (error) {
        console.error("Error starting audio streaming:", error);
        alert("Failed to start audio streaming. Please check microphone permissions.");
        setIsListening(false);
        isListeningRef.current = false;
      }
    }
  };

  const stopListening = () => {
    if (audioStreamerRef.current) {
      audioStreamerRef.current.stop();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    // Stop audio player
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }
  };

  const interruptAI = () => {
    console.log("Interrupting AI...");

    // Stop current audio
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }

    // Cancel current LLM generation
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "interrupt",
        })
      );
    }

    // Clear pending response
    pendingResponseRef.current = null;

    // Reset states
    setIsProcessing(false);
    isProcessingRef.current = false;

    // Clear transcript
    setTranscript("");
  };

  const toggleListening = () => {
    if (isListening) {
      // Turn off - stop everything
      setIsListening(false);
      isListeningRef.current = false;
      stopListening();
      setTranscript("");

      // Stop any ongoing audio and clear queue
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.stop();
      }
    } else {
      // Turn on - start continuous conversation
      setIsListening(true);
      isListeningRef.current = true;

      // Unlock audio player on user interaction
      if (audioPlayerRef.current) {
        audioPlayerRef.current.unlock();
      }

      startListening();
    }
  };

  return (
    <div className="flex flex-col h-full bg-black text-white">
      <div className="border-b border-neutral-800 p-6">
        <h2 className="text-2xl font-semibold">Voice Agent</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-4 max-w-4xl mx-auto">
          {conversation.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-4 ${
                  msg.role === "user"
                    ? "bg-neutral-700 text-white"
                    : "bg-neutral-800 text-neutral-100"
                }`}
              >
                <div className="font-medium mb-1 text-sm opacity-75">
                  {msg.role === "user" ? "You" : "Agent"}
                </div>
                <div>{msg.content}</div>
              </div>
            </div>
          ))}
          {transcript && (
            <div className="flex justify-end">
              <div className="max-w-[70%] rounded-lg p-4 bg-neutral-700/50 text-white">
                <div className="font-medium mb-1 text-sm opacity-75">You</div>
                <div className="italic">{transcript}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-neutral-800 p-6 flex flex-col items-center space-y-4">
        <button
          className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl transition-all ${
            isListening
              ? "bg-red-600 hover:bg-red-700 animate-pulse"
              : "bg-green-600 hover:bg-green-700"
          }`}
          onClick={toggleListening}
        >
          {isListening ? "📞" : "☎️"}
        </button>

        <p className="text-neutral-400 text-sm">
          {isListening ? "On call - Click to end" : "Click to start call"}
        </p>
      </div>
    </div>
  );
}

export default Agent;
