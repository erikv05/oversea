import { useState, useEffect, useRef } from "react";
import { AudioPlayer } from "../AudioPlayer";
import { AudioStreamer } from "../AudioStreamer";

interface AgentProps {
  agentId?: string | null;
  onBack?: () => void;
}

function Agent({ agentId, onBack }: AgentProps) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [conversation, setConversation] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const conversationRef = useRef<Array<{ role: string; content: string }>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [conversationId] = useState("bhOBfzddFdvjBV2Mqdmc");
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isInitialized = useRef(false);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const currentResponseRef = useRef("");
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const pendingResponseRef = useRef<string | null>(null);
  const callTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Sample agent data - in real app this would come from props/API
  const agentData = {
    name: agentId === '1' ? 'Bozidar' : 'Untitled Agent',
    conversations: agentId === '1' ? 4 : 2,
    minutesSpoken: agentId === '1' ? 1.1 : 0
  };

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
            "Failed to connect to the backend. Make sure the server is running on localhost:8000\\n\\nError code: " +
              event.code +
              "\\nReason: " +
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
          if (isProcessingRef.current || (audioPlayerRef.current && audioPlayerRef.current.isPlaying())) {
            interruptAI();
            setTranscript(data.text);
          }
          break;

        case "stream_start": {
          console.log("Stream started");

          if (!pendingResponseRef.current) {
            console.log("Response no longer needed, user continued speaking");
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "interrupt" }));
            }
            break;
          }

          const userMessage = pendingResponseRef.current;
          setConversation((prev) => {
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
          const audioUrl = `http://localhost:8000${data.audio_url}`;
          console.log("Received audio chunk:", audioUrl, "Text:", data.text);

          if (audioPlayerRef.current) {
            pendingResponseRef.current = null;
            audioPlayerRef.current.addToQueue(audioUrl, data.text);
          }
          break;
        }

        case "interim_transcript":
          {
            console.log("Interim transcript received:", data.text);
            setTranscript(data.text);
            
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
          
          const userMessage = data.text;
          pendingResponseRef.current = userMessage;
          
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
            setConversation((prev) => {
              const newConv = [...prev];
              if (
                newConv.length > 0 &&
                newConv[newConv.length - 1].role === "assistant"
              ) {
                newConv.pop();
              }
              if (
                newConv.length > 0 &&
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

          pendingResponseRef.current = null;
          if (!audioPlayerRef.current || !audioPlayerRef.current.isPlaying()) {
            setIsProcessing(false);
            isProcessingRef.current = false;
          }
          break;
        }
      }
    };

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
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
      isInitialized.current = false;
    };
  }, []);

  useEffect(() => {
    if (isListening && !callTimerRef.current) {
      callTimerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else if (!isListening && callTimerRef.current) {
      clearInterval(callTimerRef.current);
      callTimerRef.current = null;
    }

    return () => {
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
    };
  }, [isListening]);

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
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }
  };

  const interruptAI = () => {
    console.log("Interrupting AI...");

    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "interrupt",
        })
      );
    }

    pendingResponseRef.current = null;
    setIsProcessing(false);
    isProcessingRef.current = false;
    setTranscript("");
  };

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
      isListeningRef.current = false;
      stopListening();
      setTranscript("");
      setCallDuration(0);

      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.stop();
      }
    } else {
      setIsListening(true);
      isListeningRef.current = true;

      if (audioPlayerRef.current) {
        audioPlayerRef.current.unlock();
      }

      startListening();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const AudioWaveform = () => (
    <div className="flex items-center justify-center space-x-1 h-16">
      {[...Array(20)].map((_, i) => (
        <div
          key={i}
          className={`w-1 bg-gradient-to-t from-blue-600 to-blue-400 rounded-full animate-pulse ${
            isListening ? 'opacity-100' : 'opacity-30'
          }`}
          style={{
            height: `${Math.random() * 40 + 8}px`,
            animationDelay: `${i * 0.1}s`,
            animationDuration: isListening ? `${0.5 + Math.random() * 0.5}s` : '1s'
          }}
        />
      ))}
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-black text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-neutral-800">
        <button 
          onClick={onBack}
          className="flex items-center space-x-2 text-neutral-400 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Agents</span>
        </button>
        <h1 className="text-sm font-medium text-neutral-400 tracking-wider uppercase">
          Voice Agent in Conversation
        </h1>
        <div className="w-32" /> {/* Spacer for centering */}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        
        {/* Agent Card */}
        <div className="bg-neutral-900/80 rounded-3xl p-6 border border-neutral-800/30 mb-8 w-full max-w-md">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-medium text-white">{agentData.name}</h2>
            <div className="flex items-center space-x-2">
              <button className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/20 rounded-full transition-colors text-sm">
                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
                </svg>
                <span className="text-blue-400">Share Agent</span>
              </button>
              <button className="p-2 hover:bg-neutral-800 rounded-full transition-colors">
                <svg className="w-5 h-5 text-neutral-400" fill="none" viewBox="0 0 24 24">
                  <circle cx="5" cy="12" r="2" fill="currentColor" />
                  <circle cx="12" cy="12" r="2" fill="currentColor" />
                  <circle cx="19" cy="12" r="2" fill="currentColor" />
                </svg>
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-6 text-sm text-neutral-400">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <span>{agentData.conversations} conversations</span>
            </div>
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{agentData.minutesSpoken} minutes spoken</span>
            </div>
          </div>
        </div>

        {/* Conversation ID */}
        <div className="bg-neutral-900/50 rounded-3xl px-4 py-3 mb-8">
          <div className="text-sm text-neutral-400 mb-1">Conversation ID</div>
          <div className="text-sm font-mono text-neutral-300">{conversationId}</div>
        </div>

        {/* Audio Waveform */}
        <div className="mb-8">
          <AudioWaveform />
        </div>

        {/* Status */}
        <div className="flex items-center space-x-2 mb-2">
          {isListening && (
            <>
              <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse" />
              <span className="text-sm text-neutral-300">listening...</span>
            </>
          )}
        </div>

        {/* Timer */}
        {isListening && (
          <div className="text-2xl font-mono text-white mb-8">
            {formatTime(callDuration)}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col space-y-4 w-full max-w-md">
          <button
            onClick={toggleListening}
            className={`w-full py-3 rounded-full font-medium transition-all flex items-center justify-center space-x-2 ${
              isListening
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }`}
          >
            {isListening ? (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>End Conversation</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <span>Start Conversation</span>
              </>
            )}
          </button>

          <button className="w-full py-3 rounded-full font-medium bg-neutral-800 hover:bg-neutral-700 text-white transition-all flex items-center justify-center space-x-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
            <span>Share Agent</span>
          </button>
        </div>

        {/* Transcript Display */}
        {transcript && (
          <div className="mt-8 bg-neutral-900/50 rounded-3xl p-4 w-full max-w-md">
            <div className="text-sm text-neutral-400 mb-1">You</div>
            <div className="text-white italic">{transcript}</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Agent;