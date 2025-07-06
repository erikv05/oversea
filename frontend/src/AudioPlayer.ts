// Real-time audio streaming player for voice calls
export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private isUnlocked = false;
  private activeSources: Set<AudioBufferSourceNode> = new Set();
  private onComplete: (() => void) | null = null;
  private playbackQueue: Array<{ url: string; text: string }> = [];
  private isProcessingQueue = false;
  private currentGeneration = 0; // Track generation to ignore old audio

  constructor() {
    console.log('AudioPlayer constructor called');
  }

  // Reset the player for a new conversation turn
  reset() {
    this.currentGeneration++;
    console.log(`[AudioPlayer] Reset called, new generation: ${this.currentGeneration}`);
    
    // Stop all active audio sources immediately
    this.stopAllAudio();
    
    // Clear the queue
    this.playbackQueue = [];
    this.isProcessingQueue = false;
  }

  private stopAllAudio() {
    console.log(`[AudioPlayer] Stopping ${this.activeSources.size} active audio sources`);
    
    // Stop and disconnect all active sources
    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch (e) {
        // Source might have already ended
      }
    }
    this.activeSources.clear();
  }

  async addToQueue(url: string, text: string) {
    const generation = this.currentGeneration;
    console.log(`[AudioPlayer] Adding to queue - Generation: ${generation}, URL: ${url}`);
    
    // Try to unlock if not already unlocked
    if (!this.isUnlocked) {
      this.unlock();
    }
    
    this.playbackQueue.push({ url, text });
    
    // Process queue if not already processing
    if (!this.isProcessingQueue && this.isUnlocked) {
      this.processQueue(generation);
    }
  }

  private async processQueue(generation: number) {
    if (this.isProcessingQueue) return;
    
    this.isProcessingQueue = true;
    console.log(`[AudioPlayer] Starting queue processing for generation ${generation}`);
    
    while (this.playbackQueue.length > 0) {
      // Check if we should stop (new generation started)
      if (generation !== this.currentGeneration) {
        console.log(`[AudioPlayer] Generation mismatch (${generation} vs ${this.currentGeneration}), stopping queue processing`);
        break;
      }
      
      const item = this.playbackQueue.shift()!;
      
      try {
        await this.playAudio(item.url, item.text, generation);
      } catch (error) {
        console.error('[AudioPlayer] Error playing audio:', error);
        // Continue with next item on error
      }
    }
    
    this.isProcessingQueue = false;
    
    // Check if this was the last audio for this generation
    if (generation === this.currentGeneration && this.playbackQueue.length === 0 && this.activeSources.size === 0) {
      console.log('[AudioPlayer] All audio finished for current generation');
      if (this.onComplete) {
        this.onComplete();
      }
    }
  }

  private async playAudio(url: string, text: string, generation: number): Promise<void> {
    // Double-check generation before playing
    if (generation !== this.currentGeneration) {
      console.log(`[AudioPlayer] Skipping outdated audio from generation ${generation}`);
      return;
    }

    console.log(`[AudioPlayer] Playing audio: ${url} (${text.substring(0, 50)}...)`);
    
    try {
      // Fetch audio
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const arrayBuffer = await response.arrayBuffer();
      
      // Check generation again after async operation
      if (generation !== this.currentGeneration) {
        console.log(`[AudioPlayer] Generation changed during fetch, skipping playback`);
        return;
      }
      
      if (!this.audioContext) {
        const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
        this.audioContext = new AudioContextClass();
      }
      
      if (this.audioContext.state !== 'running') {
        await this.audioContext.resume();
      }
      
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      
      // Final generation check before playing
      if (generation !== this.currentGeneration) {
        console.log(`[AudioPlayer] Generation changed during decode, skipping playback`);
        return;
      }
      
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      
      // Track this source
      this.activeSources.add(source);
      
      // Create a promise that resolves when playback ends
      return new Promise<void>((resolve) => {
        source.onended = () => {
          console.log('[AudioPlayer] Audio chunk finished');
          this.activeSources.delete(source);
          resolve();
        };
        
        source.start(0);
      });
      
    } catch (error) {
      console.error('[AudioPlayer] Error in playAudio:', error);
      throw error;
    }
  }

  setOnComplete(callback: () => void) {
    this.onComplete = callback;
  }

  isPlaying(): boolean {
    return this.activeSources.size > 0 || this.isProcessingQueue;
  }

  stop() {
    console.log('[AudioPlayer] Stop called');
    this.reset();
  }

  unlock() {
    console.log('[AudioPlayer] Unlock called');
    
    if (!this.audioContext) {
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass();
      console.log('[AudioPlayer] Created AudioContext, state:', this.audioContext.state);
    }
    
    // Safari workaround: Play a silent buffer to unlock
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    if (isSafari && this.audioContext.state === 'suspended') {
      console.log('[AudioPlayer] Safari detected, playing silent buffer');
      const buffer = this.audioContext.createBuffer(1, 1, 22050);
      const source = this.audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(this.audioContext.destination);
      source.start(0);
    }
    
    // Always try to resume
    this.audioContext.resume().then(() => {
      this.isUnlocked = true;
      console.log('[AudioPlayer] AudioContext resumed, state:', this.audioContext!.state);
      
      // Process any queued audio
      if (this.playbackQueue.length > 0 && !this.isProcessingQueue) {
        this.processQueue(this.currentGeneration);
      }
    }).catch(e => {
      console.error('[AudioPlayer] Failed to unlock:', e);
      this.isUnlocked = true;
    });
  }
}