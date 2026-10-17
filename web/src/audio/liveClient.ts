// The phone's voice line to Ustaad (shared/contracts/ws-events.md): mic audio up while the button is held,
// Ustaad's audio and frames down, reconnect with the resume handle when the network drops.
import captureUrl from './capture.worklet.ts?worker&url'
import playbackUrl from './playback.worklet.ts?worker&url'

import { demoSession } from '@/api/session'

import { TurnBuffer } from './turnBuffer'

export type GateId = 'G_MAINS_OFF' | 'G_CAP_DISCHARGE'
export type MediaKind = 'photo' | 'video' | 'document'
export type Hazard = 'none' | 'HV' | 'capacitor' | 'refrigerant'
export type StepSource = {
  kind: 'whatsapp_voice' | 'whatsapp_text' | 'manual' | 'job' | 'synthetic' | 'manual_photo' | 'general'
  label: string
  audio_uri: string | null
  doc: string | null
  page: number | null
}
export type QuoteItem = {
  quote_id: string
  vendor: string
  distance_km: number | null
  price_inr: number | null
  available: boolean | null
  eta: string | null
  from_voice: boolean
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
  | { v: 1; type: 'step_card'; job_id: string; n: number; of: number; instruction: string; instruction_translated?: string | null; hazard: Hazard; source: StepSource }
  | { v: 1; type: 'safety_gate'; gate_id: GateId; message: string; required_evidence: string }
  | { v: 1; type: 'gate_result'; gate_id: GateId; passed: boolean; reason: string | null }
  | { v: 1; type: 'safety_stop'; reason: string; message: string }
  | { v: 1; type: 'job_closed'; job_id: string; card_id: string }
  | {
      v: 1
      type: 'media_request'
      request_id: string
      kind: MediaKind
      target: string
      framing_tip: string
      max_seconds: number | null
    }
  | { v: 1; type: 'media_result'; request_id: string; matches_expected: boolean; confidence: number; retake_reason: string | null }
  | { v: 1; type: 'quotes'; quote_request_id: string; items: QuoteItem[] }

export type LiveStatus = 'connecting' | 'ready' | 'reconnecting' | 'failed' | 'busy'

export interface LiveConnection {
  startTalking(): Promise<void>
  stopTalking(): void
  mediaOffer(kind: 'photo' | 'document'): void
  mediaReady(requestId: string, uri: string, kind: MediaKind): void
  mediaCancel(requestId: string): void
  stepDone(n: number): void
  close(): void
}

const WS_URL = import.meta.env.VITE_API_WS_URL ?? ''
const MOCK = import.meta.env.VITE_MOCK_LIVE === '1'
const PING_MS = 20_000
const RETRIES = 5
const RETRY_MS = 2_000

// The handle is kept per job so a page refresh or Retry resumes the same Ustaad instead of a new one with no memory
// (phone test 3, Oct 15). Storage can throw in private windows; then only in-page reconnects resume.
const handleKey = (jobId: string) => `ustaad.resume.${jobId}`
function storeHandle(jobId: string, handle: string | null) {
  try {
    if (handle) sessionStorage.setItem(handleKey(jobId), handle)
    else sessionStorage.removeItem(handleKey(jobId))
  } catch {
    // not stored: a refresh starts a new session
  }
}
function storedHandle(jobId: string): string | null {
  try {
    return sessionStorage.getItem(handleKey(jobId))
  } catch {
    return null
  }
}

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
  let resume = storedHandle(jobId)
  let lastError: string | null = null
  let failures = 0
  let closed = false
  let held = false // the button is down
  let talking = false // ptt start was sent
  let sessionReady = false
  const turn = new TurnBuffer()
  const timers: number[] = []

  const send = (data: string | ArrayBuffer) => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(data)
  }
  const sendFrame = (frame: object) => send(JSON.stringify({ v: 1, ...frame }))
  // A turn spoken while reconnecting waits for the new session instead of being lost.
  const sendTurn = (data: string | ArrayBuffer) => (sessionReady ? send(data) : turn.push(data))
  const sendTurnFrame = (frame: object) => sendTurn(JSON.stringify({ v: 1, ...frame }))

  const handle = (frame: ServerFrame) => {
    if (frame.type === 'session_ready') {
      failures = 0
      sessionReady = true
      turn.flush(send)
      onStatus('ready')
    }
    if (frame.type === 'resume_handle') {
      resume = frame.handle
      storeHandle(jobId, resume)
    }
    if (frame.type === 'interrupted') playback?.postMessage('clear')
    if (frame.type === 'error') lastError = frame.code
    // An expired handle would fail every reconnect; the next one starts a new session instead.
    if (frame.type === 'error' && frame.code === 'live_unavailable') {
      resume = null
      storeHandle(jobId, null)
    }
    onFrame(frame)
  }

  const connect = () => {
    const params = new URLSearchParams({ token: demoSession()?.token ?? '', lang, job_id: jobId })
    if (resume) params.set('resume', resume)
    ws = new WebSocket(`${WS_URL}?${params}`)
    ws.binaryType = 'arraybuffer'
    ws.onmessage = (e: MessageEvent<string | ArrayBuffer>) => {
      if (typeof e.data === 'string') handle(JSON.parse(e.data))
      else playback?.postMessage(e.data, [e.data])
    }
    ws.onclose = () => {
      sessionReady = false
      if (closed) return
      // A bad token or a full server won't get better by retrying; a full server is not his network's fault.
      if (lastError === 'rate_limited' || lastError === 'auth' || ++failures > RETRIES) {
        // Nothing will carry a held turn now; it is dropped rather than sent much later.
        turn.clear()
        return onStatus(lastError === 'rate_limited' ? 'busy' : 'failed')
      }
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
        if (talking) sendTurn(e.data)
      }
      // The first press waits for the permission prompt; he may have let go already.
      if (held && !talking) {
        talking = true
        sendTurnFrame({ type: 'ptt', state: 'start' })
      }
    },
    stopTalking() {
      held = false
      if (!talking) return
      talking = false
      sendTurnFrame({ type: 'ptt', state: 'end' })
    },
    mediaOffer(kind) {
      sendFrame({ type: 'media_offer', kind })
    },
    mediaReady(requestId, uri, kind) {
      sendFrame({ type: 'media_ready', request_id: requestId, uri, kind })
    },
    mediaCancel(requestId) {
      sendFrame({ type: 'media_cancel', request_id: requestId })
    },
    stepDone(n) {
      sendFrame({ type: 'step_done', n })
    },
    close() {
      closed = true
      timers.forEach((t) => window.clearTimeout(t))
      ws?.close()
    },
  }
}
