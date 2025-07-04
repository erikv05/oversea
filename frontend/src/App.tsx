import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [conversation, setConversation] = useState<Array<{role: string, content: string}>>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const recognitionRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    // Initialize WebSocket connection
    wsRef.current = new WebSocket('ws://localhost:8000/ws')
    
    wsRef.current.onopen = () => {
      console.log('WebSocket connected successfully')
    }
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
      alert('Failed to connect to the backend. Make sure the server is running on localhost:8000')
    }
    
    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected')
    }
    
    wsRef.current.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'response') {
        // Add AI response to conversation
        setConversation(prev => [...prev, { role: 'assistant', content: data.text }])
        
        // Play TTS audio
        if (data.audio_url) {
          const audio = new Audio(data.audio_url)
          audioRef.current = audio
          await audio.play()
          audio.onended = () => {
            setIsProcessing(false)
            // Resume listening after TTS finishes
            if (isListening) {
              startListening()
            }
          }
        }
      }
    }

    // Initialize speech recognition
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.error('Speech Recognition API not supported in this browser')
      alert('Your browser does not support speech recognition. Please use Chrome, Edge, or Safari.')
      return
    }
    
    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      
      recognition.onresult = (event: any) => {
        const current = event.resultIndex
        const transcript = event.results[current][0].transcript
        setTranscript(transcript)
        
        // Check if the user has finished speaking
        if (event.results[current].isFinal) {
          handleUserInput(transcript)
        }
      }
      
      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        
        // Handle specific error types
        if (event.error === 'network') {
          console.log('Network error - attempting to restart speech recognition...')
          setIsListening(false)
          // Auto-restart after network error
          setTimeout(() => {
            if (!isProcessing) {
              console.log('Restarting speech recognition...')
              setIsListening(true)
              startListening()
            }
          }, 1000)
        } else if (event.error === 'not-allowed') {
          setIsListening(false)
          alert('Microphone access denied. Please allow microphone access and refresh the page.')
        } else if (event.error === 'no-speech') {
          console.log('No speech detected')
          // Don't stop listening on no-speech
        } else if (event.error === 'aborted') {
          console.log('Speech recognition aborted')
          setIsListening(false)
        } else {
          console.error('Unknown speech recognition error:', event.error)
          setIsListening(false)
        }
      }
      
      recognitionRef.current = recognition
    } catch (error) {
      console.error('Failed to initialize speech recognition:', error)
      alert('Failed to initialize speech recognition. Please check your browser settings.')
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const startListening = () => {
    if (recognitionRef.current && !isProcessing) {
      try {
        recognitionRef.current.start()
        setTranscript('')
      } catch (error) {
        console.error('Error starting speech recognition:', error)
        // If already started, stop and restart
        try {
          recognitionRef.current.stop()
          setTimeout(() => {
            recognitionRef.current.start()
            setTranscript('')
          }, 100)
        } catch (e) {
          console.error('Failed to restart speech recognition:', e)
        }
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
  }

  const handleUserInput = (text: string) => {
    if (!text.trim() || isProcessing) return
    
    setIsProcessing(true)
    stopListening()
    
    // Add user message to conversation
    const updatedConversation = [...conversation, { role: 'user', content: text }]
    setConversation(updatedConversation)
    
    // Send to backend
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: text,
        conversation: updatedConversation
      }))
    }
  }

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false)
      stopListening()
    } else {
      setIsListening(true)
      startListening()
    }
  }

  return (
    <div className="app">
      <div className="container">
        <h1>Voice Agent</h1>
        
        <div className="conversation">
          {conversation.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <strong>{msg.role === 'user' ? 'You' : 'Agent'}:</strong> {msg.content}
            </div>
          ))}
          {transcript && (
            <div className="message user interim">
              <strong>You:</strong> {transcript}
            </div>
          )}
        </div>
        
        <button 
          className={`mic-button ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={toggleListening}
          disabled={isProcessing}
        >
          {isProcessing ? '⏳' : isListening ? '🔴' : '🎤'}
        </button>
        
        <p className="status">
          {isProcessing ? 'Processing...' : isListening ? 'Listening...' : 'Click to start'}
        </p>
      </div>
    </div>
  )
}

export default App