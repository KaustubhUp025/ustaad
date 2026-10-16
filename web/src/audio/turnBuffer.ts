// A turn spoken while the socket reconnects (BUILD-GUIDE T27, from T11): its ptt frames and up to about 5 s of mic
// audio wait here and go out in order once the new session is ready, so he need not wait 2-4 s to talk.

// 16 kHz mono PCM16 is 32,000 bytes a second.
export const MAX_BUFFERED_BYTES = 5 * 32_000

export class TurnBuffer {
  private held: (string | ArrayBuffer)[] = []
  private audioBytes = 0

  // ptt frames are always kept, so a turn that started is also ended; audio past the cap is dropped.
  push(data: string | ArrayBuffer) {
    if (data instanceof ArrayBuffer) {
      if (this.audioBytes + data.byteLength > MAX_BUFFERED_BYTES) return
      this.audioBytes += data.byteLength
    }
    this.held.push(data)
  }

  flush(send: (data: string | ArrayBuffer) => void) {
    this.held.forEach(send)
    this.clear()
  }

  clear() {
    this.held = []
    this.audioBytes = 0
  }
}
