// The phone's voice line to Ustaad (shared/contracts/ws-events.md): mic audio up while the button is held,
// Ustaad's audio and frames down, reconnect with the resume handle when the network drops.
import captureUrl from './capture.worklet.ts?worker&url'
import playbackUrl from './playback.worklet.ts?worker&url'

export type GateId = 'G_MAINS_OFF' | 'G_CAP_DISCHARGE'
export type Hazard = 'none' | 'HV' | 'capacitor' | 'refrigerant'
export type StepSource = {
  kind: 'whatsapp_voice' | 'whatsapp_text' | 'manual' | 'job' | 'synthetic' | 'manual_photo' | 'general'
  label: string
  audio_uri: string | null
  doc: string | null
  page: number | null
}

// Frames this module and the job screen read; the other server frames arrive with their own tasks.
export type ServerFrame =
  | { v: 1; type: 'session_ready'; session_id: string; live_model: string; resumable: boolean }
  | { v: 1; type: 'caption'; who: 'user' | 'ustaad'; text: string; final: boolean }
  | { v: 1; type: 'interrupted' }
  | { v: 1; type: 'turn_complete' }
  | { v: 1; type: 'resume_handle'; handle: string }
  | { v: 1; type: 'error'; code: 'live_unavailable' | 'rate_limited' | 'auth' | 'bad_request'; message: string }
  | { v: 1; type: 'pong' }
  | { v: 1; type: 'step_card'; job_id: string; n: number; of: number; instruction: string; hazard: Hazard; source: StepSource }
  | { v: 1; type: 'safety_gate'; gate_id: GateId; message: string; required_evidence: string }
  | { v: 1; type: 'gate_result'; gate_id: GateId; passed: boolean; reason: string | null }
  | { v: 1; type: 'safety_stop'; reason: string; message: string }

export type LiveStatus = 'connecting' | 'ready' | 'reconnecting' | 'failed'

export interface LiveConnection {
  startTalking(): Promise<void>
  stopTalking(): void
  close(): void
}

const WS_URL = import.meta.env.VITE_API_WS_URL ?? ''
const MOCK = import.meta.env.VITE_MOCK_LIVE === '1'
// Any non-empty token passes today; T27's POST /api/demo/session hands out the signed one.
const TOKEN = 'demo'
const PING_MS = 20_000
const RETRIES = 5
const RETRY_MS = 2_000

interface Audio {
  capture: MessagePort
  playback: MessagePort
}

// Contexts can only start on a user gesture, so this runs on the first mic press.
async function openAudio(): Promise<Audio> {
  const mic = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })
  const inCtx = new AudioContext()
  await inCtx.audioWorklet.addModule(captureUrl)
  const capture = new AudioWorkletNode(inCtx, 'capture', { numberOfOutputs: 0 })
  inCtx.createMediaStreamSource(mic).connect(capture)

  const outCtx = new AudioContext({ sampleRate: 24000 })
  await outCtx.audioWorklet.addModule(playbackUrl)
  const playback = new AudioWorkletNode(outCtx, 'playback')
  playback.connect(outCtx.destination)
  await Promise.all([inCtx.resume(), outCtx.resume()])
  return { capture: capture.port, playback: playback.port }
}

export function openLive(
  lang: string,
  jobId: string,
  onFrame: (frame: ServerFrame) => void,
  onStatus: (status: LiveStatus) => void,
): LiveConnection {
  let ws: WebSocket | null = null
  let audio: Promise<Audio> | null = null
  let playback: MessagePort | null = null
  let resume: string | null = null
  let lastError: string | null = null
  let failures = 0
  let closed = false
  let held = false // the button is down
  let talking = false // ptt start was sent
  const timers: number[] = []

  const send = (data: string | ArrayBuffer) => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(data)
  }
  const sendFrame = (frame: object) => send(JSON.stringify({ v: 1, ...frame }))

  const handle = (frame: ServerFrame) => {
    if (frame.type === 'session_ready') {
      failures = 0
      onStatus('ready')
    }
    if (frame.type === 'resume_handle') resume = frame.handle
    if (frame.type === 'interrupted') playback?.postMessage('clear')
    if (frame.type === 'error') lastError = frame.code
    onFrame(frame)
  }

  const connect = () => {
    const params = new URLSearchParams({ token: TOKEN, lang, job_id: jobId })
    if (resume) params.set('resume', resume)
    ws = new WebSocket(`${WS_URL}?${params}`)
    ws.binaryType = 'arraybuffer'
    ws.onmessage = (e: MessageEvent<string | ArrayBuffer>) => {
      if (typeof e.data === 'string') handle(JSON.parse(e.data))
      else playback?.postMessage(e.data, [e.data])
    }
    ws.onclose = () => {
      if (closed) return
      // A bad token or a full server won't get better by retrying.
      const hopeless = lastError === 'auth' || lastError === 'rate_limited'
      if (hopeless || ++failures > RETRIES) return onStatus('failed')
      onStatus('reconnecting')
      timers.push(window.setTimeout(connect, RETRY_MS))
    }
  }

  // VITE_MOCK_LIVE=1: replay the recorded G2 session (run `make mock`); nothing is sent anywhere.
  const replay = async () => {
    const lines = (await (await fetch('/mock/live_session.jsonl')).text()).trim().split('\n')
    if (closed) return
    for (const line of lines) {
      const { t_ms, frame } = JSON.parse(line) as { t_ms: number; frame: ServerFrame }
      timers.push(window.setTimeout(() => handle(frame), t_ms))
    }
  }

  onStatus('connecting')
  if (MOCK) {
    void replay()
  } else {
    connect()
    timers.push(window.setInterval(() => sendFrame({ type: 'ping' }), PING_MS))
  }

  return {
    async startTalking() {
      held = true
      // Barge-in: the worker pressing the mic silences Ustaad at once, without waiting for the server.
      playback?.postMessage('clear')
      audio ??= openAudio()
      const { capture, playback: out } = await audio.catch((err: unknown) => {
        audio = null
        throw err
      })
      playback = out
      capture.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (talking) send(e.data)
      }
      // The first press waits for the permission prompt; he may have let go already.
      if (held && !talking) {
        talking = true
        sendFrame({ type: 'ptt', state: 'start' })
      }
    },
    stopTalking() {
      held = false
      if (!talking) return
      talking = false
      sendFrame({ type: 'ptt', state: 'end' })
    },
    close() {
      closed = true
      timers.forEach((t) => window.clearTimeout(t))
      ws?.close()
    },
  }
}
