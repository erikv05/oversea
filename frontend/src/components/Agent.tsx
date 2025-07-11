import { useState, useEffect, useRef } from "react";
import { AudioPlayer } from "../AudioPlayer";
import { AudioStreamer } from "../AudioStreamer";
import { WS_URL, API_URL } from "../config";

interface AgentProps {
  agentId?: string | null;
  onBack?: () => void;
}

function Agent({ agentId, onBack }: AgentProps) {
  const [isListening, setIsListening] = useState(false);
  const [currentUserText, setCurrentUserText] = useState("");
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [conversation, setConversation] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const conversationRef = useRef<Array<{ role: string; content: string }>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const isInitialized = useRef(false);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const currentResponseRef = useRef("");
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const callTimerRef = useRef<number | null>(null);
  const [agentData, setAgentData] = useState<any>(null);
  const [loadingAgent, setLoadingAgent] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isSpeechDetected, setIsSpeechDetected] = useState(false);

  // Fetch agent data
  useEffect(() => {
    if (agentId) {
      fetchAgentData();
    }
  }, [agentId]);

  const fetchAgentData = async () => {
    if (!agentId) return;
    
    try {
      const response = await fetch(`${API_URL}/api/agents/${agentId}`);
      if (response.ok) {
        const data = await response.json();
        setAgentData(data);
      }
    } catch (error) {
      console.error('Error fetching agent data:', error);
    } finally {
      setLoadingAgent(false);
    }
  };

  useEffect(() => {
    // Prevent double initialization in development mode
    if (isInitialized.current || !agentData || loadingAgent) {
      return;
    }
    isInitialized.current = true;

    // Initialize audio player
    audioPlayerRef.current = new AudioPlayer();
    audioPlayerRef.current.setOnComplete(() => {
      console.log("[FRONTEND] All audio finished playing");
      setIsProcessing(false);
      isProcessingRef.current = false;
      setIsAgentSpeaking(false);
      console.log("[FRONTEND] Agent speaking complete, ready for user input");
      
      // Notify backend that audio playback is complete
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "audio_playback_complete"
        }));
      }
    });

    // Initialize WebSocket connection
    console.log(`Attempting to connect to WebSocket at ${WS_URL}`);

    try {
      wsRef.current = new WebSocket(WS_URL);
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      alert("Failed to create WebSocket connection: " + error);
      return;
    }

    wsRef.current.onopen = async () => {
      console.log("WebSocket connected successfully");
      
      // Send agent configuration
      if (agentId && wsRef.current) {
        wsRef.current.send(JSON.stringify({
          type: "agent_config",
          agent_id: agentId
        }));
      }
      
      // Initialize audio streamer after WebSocket is connected
      audioStreamerRef.current = new AudioStreamer();
      
      // Set up audio level callback
      audioStreamerRef.current.setAudioLevelCallback((level) => {
        setAudioLevel(level);
      });
      
      const initialized = await audioStreamerRef.current.initialize(wsRef.current!);
      if (!initialized) {
        alert("Failed to initialize audio streaming. Please check microphone permissions.");
      }
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
        case "agent_greeting":
          console.log("Agent greeting received:", data.text);
          // Display greeting text in conversation
          setConversation(prev => [...prev, { role: "assistant", content: data.text }]);
          conversationRef.current = [...conversationRef.current, { role: "assistant", content: data.text }];
          break;

        case "greeting_audio":
          console.log("Greeting audio received:", data.audio_url);
          // Play greeting audio
          if (audioPlayerRef.current) {
            const audioUrl = `${API_URL}${data.audio_url}`;
            audioPlayerRef.current.addToQueue(audioUrl, data.text || "");
          }
          break;

        case "stop_audio_immediately":
          console.log("[FRONTEND] Backend detected voice activity - stopping audio immediately");
          // Immediately stop audio playback
          if (audioPlayerRef.current) {
            audioPlayerRef.current.stop();
          }
          break;
          
        case "speech_start":
          console.log("[FRONTEND] Speech start detected");
          setIsSpeechDetected(true);
          break;
          
        case "speech_end":
          console.log("[FRONTEND] Speech end detected");
          setIsSpeechDetected(false);
          break;
          
        case "interim_transcript": {
          // Show interim transcript
          console.log("[FRONTEND] Received interim_transcript:", data.text);
          setCurrentUserText(data.text);
          setIsUserSpeaking(true);
          break;
        }
          
        case "user_transcript":
          // Final transcript from user
          console.log("[FRONTEND] Received user_transcript:", data.text);
          
          // Add to conversation
          setConversation(prev => {
            const newConv = [...prev, { role: "user", content: data.text }];
            conversationRef.current = newConv;
            console.log("[FRONTEND] Updated conversation:", newConv);
            return newConv;
          });
          
          // Clear user text and start processing
          setCurrentUserText("");
          setIsUserSpeaking(false);
          setIsProcessing(true);
          isProcessingRef.current = true;
          setIsAgentSpeaking(true);
          currentResponseRef.current = "";
          setStreamingText("");
          console.log("[FRONTEND] Set processing states");
          
          // Reset audio player for new response
          if (audioPlayerRef.current) {
            audioPlayerRef.current.reset();
            console.log("[FRONTEND] Reset audio player");
          }
          break;
          
        case "text_chunk":
          // Update the streaming text
          currentResponseRef.current += data.text;
          setStreamingText(currentResponseRef.current);
          console.log("[FRONTEND] Received text_chunk:", data.text);
          
          // Update conversation with partial response
          setConversation(prev => {
            const newConv = [...prev];
            if (newConv.length > 0 && newConv[newConv.length - 1].role === "assistant") {
              newConv[newConv.length - 1].content = currentResponseRef.current;
            } else {
              newConv.push({ role: "assistant", content: currentResponseRef.current });
            }
            conversationRef.current = newConv;
            return newConv;
          });
          break;
          
        case "audio_chunk": {
          // Queue audio chunk for playback
          const audioUrl = `${API_URL}${data.audio_url}`;
          console.log("[FRONTEND] Received audio_chunk:", audioUrl, "text:", data.text);
          
          if (audioPlayerRef.current) {
            audioPlayerRef.current.addToQueue(audioUrl, data.text);
            console.log("[FRONTEND] Added audio to queue");
          }
          break;
        }
          
        case "stream_complete":
          console.log("[FRONTEND] Received stream_complete:", data.full_text);
          // Don't add to conversation here - it's already been added during streaming
          setStreamingText("");
          setCurrentUserText("");
          setIsUserSpeaking(false);
          setIsProcessing(false);
          isProcessingRef.current = false;
          // Note: setIsAgentSpeaking(false) happens when audio finishes playing
          
          // Continue listening if the call is still active
          if (isListeningRef.current && audioStreamerRef.current) {
            console.log("[FRONTEND] Checking audio streaming status...");
            console.log("[FRONTEND] isListening:", isListeningRef.current);
            console.log("[FRONTEND] audioStreamer exists:", !!audioStreamerRef.current);
            console.log("[FRONTEND] isStreaming:", audioStreamerRef.current?.isStreaming);
            // Audio streaming should already be running, just ensure it's active
            if (!audioStreamerRef.current.isStreaming) {
              console.log("[FRONTEND] Restarting audio streaming");
              audioStreamerRef.current.start();
            } else {
              console.log("[FRONTEND] Audio streaming is already active");
            }
          }
          break;
      }
    };

    return () => {
      console.log("Cleanup function called");
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (audioStreamerRef.current) {
        audioStreamerRef.current.destroy();
      }
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
      isInitialized.current = false;
    };
  }, [agentData, agentId, loadingAgent]);

  useEffect(() => {
    if (isListening && !callTimerRef.current) {
      callTimerRef.current = window.setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else if (!isListening && callTimerRef.current) {
      clearInterval(callTimerRef.current);
      callTimerRef.current = null;
    }
  }, [isListening]);

  const startListening = async () => {
    if (audioStreamerRef.current) {
      try {
        audioStreamerRef.current.start();
        console.log("Started audio streaming");
      } catch (error) {
        console.error("Error starting audio streaming:", error);
        alert(`Failed to start audio streaming: ${error}`);
        setIsListening(false);
        isListeningRef.current = false;
      }
    }
  };

  const stopListening = () => {
    if (audioStreamerRef.current) {
      audioStreamerRef.current.stop();
    }
    // Reset audio player
    if (audioPlayerRef.current) {
      audioPlayerRef.current.reset();
    }
    setCurrentUserText("");
    setIsUserSpeaking(false);
  };

  const interruptAI = () => {
    console.log("Interrupting AI...");
    
    // Reset audio player for new conversation turn
    if (audioPlayerRef.current) {
      audioPlayerRef.current.reset();
    }
    
    // Cancel current LLM generation
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "interrupt"
      }));
    }
    
    // Reset states
    setIsProcessing(false);
    isProcessingRef.current = false;
    setStreamingText("");
  };

  const toggleListening = () => {
    if (isListening) {
      // Turn off
      setIsListening(false);
      isListeningRef.current = false;
      stopListening();
      setCallDuration(0);
    } else {
      // Turn on
      setIsListening(true);
      isListeningRef.current = true;
      
      // Unlock audio player on user interaction
      if (audioPlayerRef.current) {
        audioPlayerRef.current.unlock();
      }
      
      // Send call started message to backend
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "call_started"
        }));
      }
      
      startListening();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const AudioWaveform = () => {
    // Create different heights based on audio level and speech detection
    const barCount = 20;
    const baseHeight = 8;
    const maxAdditionalHeight = 40;
    
    return (
      <div className="flex items-center justify-center space-x-1 h-16">
        {[...Array(barCount)].map((_, i) => {
          // Create a wave effect with higher bars in the middle
          const distanceFromCenter = Math.abs(i - barCount / 2);
          const centerMultiplier = 1 - (distanceFromCenter / (barCount / 2)) * 0.5;
          
          // Base height varies with audio level
          const levelHeight = audioLevel * maxAdditionalHeight * centerMultiplier;
          
          // Add some randomness for natural effect
          const randomVariation = (Math.random() - 0.5) * 10;
          
          // Final height calculation
          const height = baseHeight + levelHeight + (isSpeechDetected ? randomVariation : 0);
          
          return (
            <div
              key={i}
              className={`w-1 bg-gradient-to-t rounded-full transition-all duration-100 ${
                isSpeechDetected 
                  ? 'from-green-500 to-green-300' 
                  : 'from-blue-600 to-blue-400'
              } ${
                isListening ? 'opacity-100' : 'opacity-30'
              }`}
              style={{
                height: `${Math.max(baseHeight, Math.min(baseHeight + maxAdditionalHeight, height))}px`,
              }}
            />
          );
        })}
      </div>
    );
  };

  if (loadingAgent) {
    return (
      <div className="flex flex-col h-full bg-black text-white items-center justify-center">
        <div className="text-neutral-400">Loading agent...</div>
      </div>
    );
  }

  if (!agentData) {
    return (
      <div className="flex flex-col h-full bg-black text-white items-center justify-center">
        <div className="text-neutral-400">Agent not found</div>
      </div>
    );
  }

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
              <span>{agentData.minutes_spoken?.toFixed(1) || 0} minutes spoken</span>
            </div>
          </div>
        </div>

        {/* Conversation ID */}
        <div className="text-center mb-8">
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">CONVERSATION ID</p>
          <p className="text-sm text-neutral-400 font-mono">bhOBfzddFdvjBV2Mqdmc</p>
        </div>

        {/* Call Status */}
        {isListening && (
          <div className="mb-8">
            <p className="text-green-400 text-center mb-2">Call Active</p>
            <p className="text-2xl font-mono text-center">{formatTime(callDuration)}</p>
          </div>
        )}

        {/* Audio Waveform */}
        {isListening && <AudioWaveform />}

        {/* Call Button */}
        <button
          onClick={toggleListening}
          className={`w-24 h-24 rounded-full transition-all duration-300 transform hover:scale-110 mb-4 ${
            isListening
              ? "bg-red-600 hover:bg-red-700 shadow-lg shadow-red-600/50"
              : "bg-green-600 hover:bg-green-700 shadow-lg shadow-green-600/50"
          }`}
        >
          <svg className="w-12 h-12 mx-auto text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {isListening ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            )}
          </svg>
        </button>

        <p className="text-neutral-400 text-sm">
          {isListening ? "Tap to end call" : "Tap to start call"}
        </p>
      </div>
    </div>
  );
}

export default Agent;