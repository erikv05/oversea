import { useState, useEffect, useRef } from 'react'
import './App.css'
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
      console.log('All audio finished playing')
      setIsProcessing(false)
      isProcessingRef.current = false
      setIsAgentSpeaking(false)
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
        case 'interim_transcript':
          // Show interim transcript
          setCurrentUserText(data.text)
          setIsUserSpeaking(true)
          
          // If AI is speaking and user starts talking, interrupt
          const isAudioPlaying = audioPlayerRef.current?.isPlaying() || false
          if ((isProcessingRef.current || isAudioPlaying) && data.text.trim().length > 0) {
            console.log('User speaking (interim), interrupting AI...')
            interruptAI()
          }
          break
          
        case 'user_transcript':
          // Final transcript from user
          console.log('User said:', data.text)
          
          // Add to conversation
          setConversation(prev => {
            const newConv = [...prev, { role: 'user', content: data.text }]
            conversationRef.current = newConv
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
          
          // Reset audio player for new response
          if (audioPlayerRef.current) {
            audioPlayerRef.current.reset()
          }
          break
          
        case 'text_chunk':
          // Update the streaming text
          currentResponseRef.current += data.text
          setStreamingText(currentResponseRef.current)
          
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
          
        case 'audio_chunk':
          // Queue audio chunk for playback
          const audioUrl = `http://localhost:8000${data.audio_url}`
          console.log('Received audio chunk:', audioUrl)
          
          if (audioPlayerRef.current) {
            audioPlayerRef.current.addToQueue(audioUrl, data.text)
          }
          break
          
        case 'stream_complete':
          console.log('Response complete:', data.full_text)
          // Don't add to conversation here - it's already been added during streaming
          setStreamingText('')
          setCurrentUserText('')
          setIsUserSpeaking(false)
          setIsProcessing(false)
          isProcessingRef.current = false
          // Note: setIsAgentSpeaking(false) happens when audio finishes playing
          
          // Continue listening if the call is still active
          if (isListeningRef.current && audioStreamerRef.current) {
            console.log('Continuing to listen for next user input...')
            // Audio streaming should already be running, just ensure it's active
            if (!audioStreamerRef.current.isStreaming) {
              audioStreamerRef.current.start()
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
    <div className="app">
      <div className="container">
        <h1>Voice Agent (Google Cloud STT)</h1>
        
        <div className="conversation">
          {conversation.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <strong>{msg.role === 'user' ? 'You' : 'Agent'}:</strong> {msg.content}
            </div>
          ))}
          {currentUserText && isUserSpeaking && (
            <div className="message user interim">
              <strong>You:</strong> {currentUserText}
            </div>
          )}
          {streamingText && (
            <div className="message assistant streaming">
              <strong>Agent:</strong> {streamingText}
            </div>
          )}
        </div>
        
        <button 
          className={`mic-button ${isListening ? 'listening' : ''}`}
          onClick={toggleListening}
        >
          {isListening ? '📞' : '☎️'}
        </button>
        
        <p className="status">
          {isListening ? 'On call (Google Cloud STT)' : 'Click to start call'}
        </p>
        
      </div>
    </div>
  )
}

export default App