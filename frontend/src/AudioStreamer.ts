// Audio streaming class for capturing and sending microphone audio
export class AudioStreamer {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private websocket: WebSocket | null = null;
  private _isStreaming = false;
  
  constructor() {
    console.log('[AudioStreamer] Initialized');
  }
  
  get isStreaming() {
    return this._isStreaming;
  }
  
  async initialize(websocket: WebSocket) {
    this.websocket = websocket;
    
    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000 // We'll downsample to 8kHz
        } 
      });
      
      // Create audio context
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass({ sampleRate: 48000 });
      
      // Create audio source from microphone
      this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
      
      // Create script processor for capturing audio
      // Buffer size of 4096 gives us ~85ms chunks at 48kHz
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      
      // Process audio data
      this.processor.onaudioprocess = (e) => {
        if (!this._isStreaming) return;
        
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Downsample from 48kHz to 8kHz (factor of 6)
        const downsampledData = this.downsample(inputData, 48000, 8000);
        
        // Convert to LINEAR16 (16-bit PCM)
        const pcm16 = this.floatTo16BitPCM(downsampledData);
        
        // Send to server
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(pcm16);
        }
      };
      
      // Send audio configuration to server
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'audio_config',
          sampleRate: 8000,
          encoding: 'LINEAR16',
          channels: 1
        }));
      }
      
      console.log('[AudioStreamer] Initialized successfully');
      return true;
      
    } catch (error) {
      console.error('[AudioStreamer] Failed to initialize:', error);
      return false;
    }
  }
  
  start() {
    if (!this.source || !this.processor || !this.audioContext) {
      console.error('[AudioStreamer] Not initialized');
      return;
    }
    
    this._isStreaming = true;
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
    
    console.log('[AudioStreamer] Started streaming');
  }
  
  stop() {
    this._isStreaming = false;
    
    if (this.source && this.processor) {
      try {
        this.source.disconnect();
        this.processor.disconnect();
      } catch (e) {
        // Ignore disconnection errors
      }
    }
    
    console.log('[AudioStreamer] Stopped streaming');
  }
  
  destroy() {
    this.stop();
    
    // Stop all tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    
    // Close audio context
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    this.processor = null;
    this.source = null;
    this.websocket = null;
    
    console.log('[AudioStreamer] Destroyed');
  }
  
  private downsample(buffer: Float32Array, fromSampleRate: number, toSampleRate: number): Float32Array {
    const sampleRateRatio = fromSampleRate / toSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    
    let offsetResult = 0;
    let offsetBuffer = 0;
    
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      
      // Simple average for downsampling
      let accum = 0;
      let count = 0;
      
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    
    return result;
  }
  
  private floatTo16BitPCM(float32Array: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
      // Clamp the value between -1 and 1
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      // Convert to 16-bit PCM
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true); // true = little endian
    }
    
    return buffer;
  }
}