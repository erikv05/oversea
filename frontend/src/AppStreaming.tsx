import { useState, useEffect, useRef } from 'react'
import { AudioPlayer } from './AudioPlayer'
import { AudioStreamer } from './AudioStreamer'

function App() {
  const [isListening, setIsListening] = useState(false)
  const [currentUserText, setCurrentUserText] = useState('')
  const [isUserSpeaking, setIsUserSpeaking] = useState(false)
  const [conversation, setConversation] = useState<Array<{role: string, content: string}>>([])
  const conversationRef = useRef<Array<{role: string, content: string}>>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const isInitialized = useRef(false)
  const isListeningRef = useRef(false)
  const isProcessingRef = useRef(false)
  const currentResponseRef = useRef('')
  const audioPlayerRef = useRef<AudioPlayer | null>(null)
  const audioStreamerRef = useRef<AudioStreamer | null>(null)

  useEffect(() => {
    // Prevent double initialization in development mode
    if (isInitialized.current) {
      console.log('Already initialized, skipping...')
      return
    }
    isInitialized.current = true
    
    // Initialize audio player
    audioPlayerRef.current = new AudioPlayer()
    audioPlayerRef.current.setOnComplete(() => {
      console.log('[FRONTEND] All audio finished playing')
      setIsProcessing(false)
      isProcessingRef.current = false
      setIsAgentSpeaking(false)
      console.log('[FRONTEND] Agent speaking complete, ready for user input')
    })
    
    // Initialize WebSocket connection
    console.log('Attempting to connect to WebSocket at ws://localhost:8000/ws')
    
    try {
      wsRef.current = new WebSocket('ws://localhost:8000/ws')
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      alert('Failed to create WebSocket connection: ' + error)
      return
    }
    
    wsRef.current.onopen = async () => {
      console.log('WebSocket connected successfully')
      
      // Initialize audio streamer after WebSocket is connected
      audioStreamerRef.current = new AudioStreamer()
      const initialized = await audioStreamerRef.current.initialize(wsRef.current!)
      if (!initialized) {
        alert('Failed to initialize audio streaming. Please check microphone permissions.')
      }

      audioStreamerRef.current.setOnVoiceActivity(() => {
        console.log('[FRONTEND] Voice activity detected, interrupting AI...')
        interruptAI()
      })
    }
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    wsRef.current.onclose = (event) => {
      console.log('WebSocket disconnected', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      })
      if (!event.wasClean) {
        setTimeout(() => {
          alert('Failed to connect to the backend. Make sure the server is running on localhost:8000\n\nError code: ' + event.code + '\nReason: ' + (event.reason || 'Unknown'))
        }, 100)
      }
    }
    
    wsRef.current.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      
      switch (data.type) {
        case 'interim_transcript': {
          // Show interim transcript
          console.log('[FRONTEND] Received interim_transcript:', data.text)
          setCurrentUserText(data.text)
          setIsUserSpeaking(true)
          break
        }
          
        case 'user_transcript':
          // Final transcript from user
          console.log('[FRONTEND] Received user_transcript:', data.text)
          
          // Add to conversation
          setConversation(prev => {
            const newConv = [...prev, { role: 'user', content: data.text }]
            conversationRef.current = newConv
            console.log('[FRONTEND] Updated conversation:', newConv)
            return newConv
          })
          
          // Clear user text and start processing
          setCurrentUserText('')
          setIsUserSpeaking(false)
          setIsProcessing(true)
          isProcessingRef.current = true
          setIsAgentSpeaking(true)
          currentResponseRef.current = ''
          setStreamingText('')
          console.log('[FRONTEND] Set processing states')
          
          // Reset audio player for new response
          if (audioPlayerRef.current) {
            audioPlayerRef.current.reset()
            console.log('[FRONTEND] Reset audio player')
          }
          break
          
        case 'text_chunk':
          // Update the streaming text
          currentResponseRef.current += data.text
          setStreamingText(currentResponseRef.current)
          console.log('[FRONTEND] Received text_chunk:', data.text)
          
          // Update conversation with partial response
          setConversation(prev => {
            const newConv = [...prev]
            if (newConv.length > 0 && newConv[newConv.length - 1].role === 'assistant') {
              newConv[newConv.length - 1].content = currentResponseRef.current
            } else {
              newConv.push({ role: 'assistant', content: currentResponseRef.current })
            }
            conversationRef.current = newConv
            return newConv
          })
          break
          
        case 'audio_chunk': {
          // Queue audio chunk for playback
          const audioUrl = `http://localhost:8000${data.audio_url}`
          console.log('[FRONTEND] Received audio_chunk:', audioUrl, 'text:', data.text)
          
          if (audioPlayerRef.current) {
            audioPlayerRef.current.addToQueue(audioUrl, data.text)
            console.log('[FRONTEND] Added audio to queue')
          }
          break
        }
          
        case 'stream_complete':
          console.log('[FRONTEND] Received stream_complete:', data.full_text)
          // Don't add to conversation here - it's already been added during streaming
          setStreamingText('')
          setCurrentUserText('')
          setIsUserSpeaking(false)
          setIsProcessing(false)
          isProcessingRef.current = false
          // Note: setIsAgentSpeaking(false) happens when audio finishes playing
          
          // Continue listening if the call is still active
          if (isListeningRef.current && audioStreamerRef.current) {
            console.log('[FRONTEND] Checking audio streaming status...')
            console.log('[FRONTEND] isListening:', isListeningRef.current)
            console.log('[FRONTEND] audioStreamer exists:', !!audioStreamerRef.current)
            console.log('[FRONTEND] isStreaming:', audioStreamerRef.current?.isStreaming)
            // Audio streaming should already be running, just ensure it's active
            if (!audioStreamerRef.current.isStreaming) {
              console.log('[FRONTEND] Restarting audio streaming')
              audioStreamerRef.current.start()
            } else {
              console.log('[FRONTEND] Audio streaming is already active')
            }
          }
          break
      }
    }

    return () => {
      console.log('Cleanup function called')
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      if (audioStreamerRef.current) {
        audioStreamerRef.current.destroy()
      }
      isInitialized.current = false
    }
  }, [])

  const startListening = async () => {
    if (audioStreamerRef.current) {
      try {
        audioStreamerRef.current.start()
        console.log('Started audio streaming')
      } catch (error) {
        console.error('Error starting audio streaming:', error)
        alert(`Failed to start audio streaming: ${error}`)
        setIsListening(false)
        isListeningRef.current = false
      }
    }
  }

  const stopListening = () => {
    if (audioStreamerRef.current) {
      audioStreamerRef.current.stop()
    }
    // Reset audio player
    if (audioPlayerRef.current) {
      audioPlayerRef.current.reset()
    }
    setCurrentUserText('')
    setIsUserSpeaking(false)
  }

  const interruptAI = () => {
    console.log('Interrupting AI...')
    
    // Reset audio player for new conversation turn
    if (audioPlayerRef.current) {
      audioPlayerRef.current.reset()
    }
    
    // Cancel current LLM generation
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'interrupt'
      }))
    }
    
    // Reset states
    setIsProcessing(false)
    isProcessingRef.current = false
    setStreamingText('')
  }

  const toggleListening = () => {
    if (isListening) {
      // Turn off
      setIsListening(false)
      isListeningRef.current = false
      stopListening()
    } else {
      // Turn on
      setIsListening(true)
      isListeningRef.current = true
      
      // Unlock audio player on user interaction
      if (audioPlayerRef.current) {
        audioPlayerRef.current.unlock()
      }
      
      startListening()
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-white text-center mb-8">
          Voice Agent (Google Cloud STT)
        </h1>
        
        <div className="bg-gray-800 rounded-lg shadow-xl p-6 mb-8 max-h-[60vh] overflow-y-auto">
          {conversation.length === 0 && !currentUserText && !streamingText ? (
            <p className="text-gray-400 text-center">Start a conversation by clicking the phone button below</p>
          ) : (
            <div className="space-y-4">
              {conversation.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-100'
                    }`}
                  >
                    <p className="text-sm font-medium mb-1 opacity-75">
                      {msg.role === 'user' ? 'You' : 'Agent'}
                    </p>
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
              {currentUserText && isUserSpeaking && (
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-lg px-4 py-2 bg-blue-600/50 text-white">
                    <p className="text-sm font-medium mb-1 opacity-75">You</p>
                    <p className="text-sm italic">{currentUserText}</p>
                  </div>
                </div>
              )}
              {streamingText && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-700 text-gray-100">
                    <p className="text-sm font-medium mb-1 opacity-75">Agent</p>
                    <p className="text-sm">{streamingText}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="flex flex-col items-center">
          <button
            className={`w-20 h-20 rounded-full transition-all duration-300 transform hover:scale-110 ${
              isListening
                ? 'bg-red-600 hover:bg-red-700 shadow-lg shadow-red-600/50 animate-pulse'
                : 'bg-green-600 hover:bg-green-700 shadow-lg shadow-green-600/50'
            }`}
            onClick={toggleListening}
          >
            <span className="text-3xl">{isListening ? '📞' : '☎️'}</span>
          </button>
          
          <p className="mt-4 text-gray-400 text-sm">
            {isListening ? 'On call (Google Cloud STT)' : 'Click to start call'}
          </p>
        </div>
      </div>
    </div>
  )
}

export default App