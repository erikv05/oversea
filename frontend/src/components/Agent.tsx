import { useState, useEffect, useRef } from "react";
import { AudioPlayer } from "../AudioPlayer";

function Agent() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [conversation, setConversation] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const conversationRef = useRef<Array<{ role: string; content: string }>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const recognitionRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isInitialized = useRef(false);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentResponseRef = useRef("");
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const speechBufferRef = useRef("");
  const lastSpeechTimeRef = useRef(Date.now());
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

      // Resume listening
      if (recognitionRef.current && isListeningRef.current) {
        setTimeout(() => {
          try {
            recognitionRef.current.start();
            console.log("Resumed listening after all TTS");
            setTranscript("");
          } catch (e) {
            console.log("Could not restart recognition:", e);
          }
        }, 500);
      }
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
        case "stream_start":
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
          setStreamingText("");
          setIsStreaming(true);
          setIsProcessing(true);
          isProcessingRef.current = true;
          break;

        case "text_chunk":
          // Update the streaming text
          currentResponseRef.current += data.text;
          setStreamingText(currentResponseRef.current);
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

        case "audio_chunk":
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

        case "stream_complete":
          console.log("Stream complete, full text:", data.full_text);
          setIsStreaming(false);
          setStreamingText("");

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

          // If no audio was played yet, we can fully reset
          if (pendingResponseRef.current) {
            pendingResponseRef.current = null;
            setIsProcessing(false);
            isProcessingRef.current = false;
          }
          break;
      }
    };

    // Initialize speech recognition
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error("Speech Recognition API not supported in this browser");
      alert(
        "Your browser does not support speech recognition. Please use Chrome, Edge, or Safari."
      );
      return;
    }

    // Detect browser
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isChrome =
      /chrome/i.test(navigator.userAgent) &&
      /google inc/i.test(navigator.vendor);
    console.log(
      `Browser detected: ${isSafari ? "Safari" : isChrome ? "Chrome" : "Other"}`
    );

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.maxAlternatives = 1;

      // Add handlers for start/end events
      recognition.onstart = () => {
        console.log("Speech recognition started");
      };

      recognition.onend = () => {
        console.log("Speech recognition ended");
        // Always restart if session is active
        if (isListeningRef.current) {
          console.log("Restarting speech recognition...");
          setTimeout(() => {
            if (recognitionRef.current && isListeningRef.current) {
              try {
                recognitionRef.current.start();
              } catch (e) {
                console.log("Could not restart:", e);
              }
            }
          }, 100);
        }
      };

      recognition.onresult = (event: any) => {
        const current = event.resultIndex;
        const transcript = event.results[current][0].transcript;

        // Update transcript display
        setTranscript(transcript);
        lastSpeechTimeRef.current = Date.now();

        // If AI is speaking/processing and user starts talking, interrupt
        if (
          (isProcessingRef.current || pendingResponseRef.current) &&
          transcript.trim().length > 3
        ) {
          console.log("User speaking, interrupting AI...");
          interruptAI();
          speechBufferRef.current = ""; // Clear buffer on interrupt
        }

        // Only process final results
        if (event.results[current].isFinal) {
          // Add to speech buffer
          speechBufferRef.current +=
            (speechBufferRef.current ? " " : "") + transcript;
          console.log("Speech buffer:", speechBufferRef.current);

          // Clear existing silence timer
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }

          // Set new silence timer
          silenceTimerRef.current = setTimeout(() => {
            if (
              speechBufferRef.current.trim() &&
              !pendingResponseRef.current &&
              !isProcessingRef.current
            ) {
              // User has stopped speaking, process their input
              const userInput = speechBufferRef.current.trim();
              console.log("Processing user input:", userInput);

              // Mark that we have a pending response
              pendingResponseRef.current = userInput;

              // Send to backend WITH the current conversation state
              if (
                wsRef.current &&
                wsRef.current.readyState === WebSocket.OPEN
              ) {
                // Use conversation ref which is always up to date
                const currentConversation = conversationRef.current;
                console.log(
                  "Sending message with conversation history:",
                  currentConversation
                );

                wsRef.current.send(
                  JSON.stringify({
                    type: "message",
                    content: userInput,
                    conversation: currentConversation,
                  })
                );
              }

              // Clear the buffer and transcript
              speechBufferRef.current = "";
              setTranscript("");
            }
          }, 700); // Wait 700ms of silence
        }
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);

        // Handle specific error types
        if (event.error === "network") {
          console.log(
            "Network error - Chrome cannot reach Google Speech API. Try using Safari."
          );
          setIsListening(false);
          isListeningRef.current = false;
          alert(
            "Speech recognition network error in Chrome.\n\nThis usually happens due to:\n• Firewall/VPN blocking Google Speech API\n• Corporate network restrictions\n• Browser extensions\n\nTry using Safari instead, which uses Apple's speech service."
          );
        } else if (event.error === "not-allowed") {
          setIsListening(false);
          isListeningRef.current = false;
          alert(
            "Microphone access denied. Please allow microphone access and refresh the page."
          );
        } else if (event.error === "no-speech") {
          console.log("No speech detected");
          // Don't stop listening on no-speech
        } else if (event.error === "aborted") {
          console.log("Speech recognition aborted");
          setIsListening(false);
          isListeningRef.current = false;
        } else {
          console.error("Unknown speech recognition error:", event.error);
          setIsListening(false);
          isListeningRef.current = false;
        }
      };

      recognitionRef.current = recognition;
    } catch (error) {
      console.error("Failed to initialize speech recognition:", error);
      alert(
        "Failed to initialize speech recognition. Please check your browser settings."
      );
    }

    return () => {
      console.log("Cleanup function called");
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log("Closing WebSocket in cleanup");
        wsRef.current.close();
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          console.log("Error stopping recognition:", e);
        }
      }
      isInitialized.current = false;
    };
  }, []);

  const startListening = async () => {
    if (recognitionRef.current && !isProcessing) {
      try {
        // First check if we have microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        stream.getTracks().forEach((track) => track.stop()); // Stop the test stream

        recognitionRef.current.start();
        setTranscript("");
        console.log("Speech recognition started successfully");
      } catch (error: any) {
        console.error("Error starting speech recognition:", error);

        if (
          error.name === "NotAllowedError" ||
          error.name === "PermissionDeniedError"
        ) {
          alert(
            "Microphone permission denied. Please allow microphone access in your browser settings."
          );
          setIsListening(false);
          isListeningRef.current = false;
        } else if (error.message && error.message.includes("already started")) {
          // If already started, stop and restart
          try {
            recognitionRef.current.stop();
            setTimeout(() => {
              recognitionRef.current.start();
              setTranscript("");
            }, 100);
          } catch (e) {
            console.error("Failed to restart speech recognition:", e);
          }
        } else {
          alert(
            `Failed to start speech recognition: ${error.message || error}`
          );
          setIsListening(false);
          isListeningRef.current = false;
        }
      }
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.log("Error stopping recognition:", e);
      }
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
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
    setIsStreaming(false);
    setStreamingText("");

    // Clear speech buffer
    speechBufferRef.current = "";
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
