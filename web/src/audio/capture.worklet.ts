// Audio thread: the mic's Float32 at the device rate becomes 16 kHz PCM16, posted in 40 ms chunks (SPEC §8).
// TypeScript has no AudioWorklet library, so the three globals this file uses are declared here.
declare const sampleRate: number
declare class AudioWorkletProcessor {
  readonly port: MessagePort
}
declare function registerProcessor(name: string, processor: new () => AudioWorkletProcessor): void

const OUT_RATE = 16000
const CHUNK = 640 // 40 ms at 16 kHz = 1,280 bytes

class Capture extends AudioWorkletProcessor {
  private step = sampleRate / OUT_RATE
  private due = 0
  private sum = 0
  private count = 0
  private out = new Int16Array(CHUNK)
  private filled = 0

  process(inputs: Float32Array[][]): boolean {
    for (const sample of inputs[0]?.[0] ?? []) {
      // Averaging each window of input samples is enough of a low-pass for speech.
      this.sum += sample
      this.count++
      if (++this.due < this.step) continue
      this.due -= this.step
      const v = Math.max(-1, Math.min(1, this.sum / this.count))
      this.out[this.filled++] = v < 0 ? v * 0x8000 : v * 0x7fff
      this.sum = 0
      this.count = 0
      if (this.filled === CHUNK) {
        this.port.postMessage(this.out.buffer, [this.out.buffer])
        this.out = new Int16Array(CHUNK)
        this.filled = 0
      }
    }
    return true
  }
}

registerProcessor('capture', Capture)
