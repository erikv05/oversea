// Audio player with Safari-compatible playback
export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private isUnlocked = false;
  private queue: Array<{ url: string; text: string }> = [];
  private isPlaying = false;
  private onComplete: (() => void) | null = null;

  constructor() {
    console.log('AudioPlayer constructor called');
    // We'll initialize audio context when unlock() is called
  }

  async addToQueue(url: string, text: string) {
    console.log('Adding to audio queue:', url, 'Unlocked:', this.isUnlocked, 'Playing:', this.isPlaying);
    this.queue.push({ url, text });
    
    if (!this.isPlaying && this.isUnlocked) {
      this.playNext();
    } else if (!this.isUnlocked) {
      console.log('Audio not unlocked yet, waiting for user interaction');
    }
  }

  private async playNext() {
    if (this.queue.length === 0) {
      console.log('Queue empty, stopping playback');
      this.isPlaying = false;
      if (this.onComplete) {
        this.onComplete();
      }
      return;
    }

    this.isPlaying = true;
    const { url, text } = this.queue.shift()!;
    console.log('Playing audio:', url, 'Text:', text.substring(0, 50) + '...');

    try {
      console.log('Fetching audio from:', url);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      console.log('Audio fetch successful, decoding...');
      const arrayBuffer = await response.arrayBuffer();
      console.log('ArrayBuffer size:', arrayBuffer.byteLength);
      
      if (!this.audioContext) {
        throw new Error('AudioContext is null');
      }
      
      if (this.audioContext.state !== 'running') {
        console.warn('AudioContext state is:', this.audioContext.state);
      }
      
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      console.log('Audio decoded successfully, duration:', audioBuffer.duration, 'seconds');
      
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      
      source.onended = () => {
        console.log('Audio chunk finished playing');
        this.playNext();
      };
      
      console.log('Starting audio playback...');
      source.start(0);
    } catch (error) {
      console.error('Error playing audio:', error);
      console.error('Error details:', {
        message: (error as Error).message,
        stack: (error as Error).stack
      });
      // Continue with next chunk on error
      setTimeout(() => this.playNext(), 100);
    }
  }

  setOnComplete(callback: () => void) {
    this.onComplete = callback;
  }

  stop() {
    this.queue = [];
    this.isPlaying = false;
  }

  unlock() {
    console.log('unlock() called');
    
    if (!this.audioContext) {
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass();
      console.log('Created new AudioContext, state:', this.audioContext.state);
    }
    
    if (this.audioContext.state === 'suspended') {
      console.log('AudioContext is suspended, attempting to resume...');
      this.audioContext.resume().then(() => {
        this.isUnlocked = true;
        console.log('AudioContext resumed successfully, state:', this.audioContext.state);
        
        // Process any queued audio
        if (this.queue.length > 0 && !this.isPlaying) {
          console.log('Starting queued audio after unlock, queue length:', this.queue.length);
          this.playNext();
        }
      }).catch(e => {
        console.error('Failed to unlock audio context:', e);
      });
    } else {
      this.isUnlocked = true;
      console.log('AudioContext already running, state:', this.audioContext.state);
      
      // Process any queued audio
      if (this.queue.length > 0 && !this.isPlaying) {
        console.log('Starting queued audio, queue length:', this.queue.length);
        this.playNext();
      }
    }
  }
}