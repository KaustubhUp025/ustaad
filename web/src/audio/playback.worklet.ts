// Audio thread: plays Ustaad's 24 kHz PCM16 in arrival order; the message "clear" empties the queue at once (barge-in).
declare class AudioWorkletProcessor {
  readonly port: MessagePort
}
declare function registerProcessor(name: string, processor: new () => AudioWorkletProcessor): void

class Playback extends AudioWorkletProcessor {
  private queue: Float32Array[] = []
  private offset = 0

  constructor() {
    super()
    this.port.onmessage = (e: MessageEvent<ArrayBuffer | 'clear'>) => {
      if (e.data === 'clear') {
        this.queue = []
        this.offset = 0
        return
      }
      const pcm = new Int16Array(e.data)
      this.queue.push(Float32Array.from(pcm, (s) => s / 0x8000))
    }
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const out = outputs[0][0]
    let i = 0
    while (i < out.length && this.queue.length) {
      const head = this.queue[0]
      const n = Math.min(out.length - i, head.length - this.offset)
      out.set(head.subarray(this.offset, this.offset + n), i)
      i += n
      this.offset += n
      if (this.offset === head.length) {
        this.queue.shift()
        this.offset = 0
      }
    }
    return true
  }
}

registerProcessor('playback', Playback)
