import { useEffect, useRef, useState } from 'react'

import { type LiveConnection, type LiveStatus, type MediaKind, type ServerFrame, openLive } from './liveClient'
import { mediaReducer, noMedia } from './media'
import { noProfile, profileReducer } from './profile'
import { noQuotes, quotesReducer } from './quotes'
import { noRepair, repairReducer } from './safety'

export type CaptionLine = { who: 'user' | 'ustaad'; text: string; final: boolean }
type CaptionFrame = Extract<ServerFrame, { type: 'caption' }>
export type Identified = Extract<ServerFrame, { type: 'identified' }>

const SHOWN = 3 // DESIGN.md: the last 3 turns stay on screen

// A partial caption replaces the previous partial from the same speaker; the final one locks it.
export function addCaption(lines: CaptionLine[], { who, text, final }: CaptionFrame): CaptionLine[] {
  const open = lines.findLastIndex((l) => l.who === who && !l.final)
  const next = open === -1 ? [...lines, { who, text, final }] : lines.with(open, { who, text, final })
  return next.slice(-SHOWN)
}

export function useLive(lang: string, jobId: string) {
  const [status, setStatus] = useState<LiveStatus>('connecting')
  const [captions, setCaptions] = useState<CaptionLine[]>([])
  const [repair, setRepair] = useState(noRepair)
  const [media, setMedia] = useState(noMedia)
  const [quotes, setQuotes] = useState(noQuotes)
  const [profile, setProfile] = useState(noProfile)
  const [identified, setIdentified] = useState<Identified | null>(null)
  const [talking, setTalking] = useState(false)
  const [micBlocked, setMicBlocked] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const conn = useRef<LiveConnection | null>(null)

  useEffect(() => {
    const c = openLive(
      lang,
      jobId,
      (frame) => {
        if (frame.type === 'caption') setCaptions((lines) => addCaption(lines, frame))
        if (frame.type === 'identified') setIdentified(frame)
        setRepair((view) => repairReducer(view, frame))
        setMedia((view) => mediaReducer(view, frame))
        setQuotes((view) => quotesReducer(view, frame))
        setProfile((view) => profileReducer(view, frame))
      },
      setStatus,
    )
    conn.current = c
    return () => c.close()
  }, [lang, jobId, attempt])

  return {
    status,
    captions,
    repair,
    media,
    quotes,
    profile,
    identified,
    talking,
    micBlocked,
    async startTalking() {
      setTalking(true)
      try {
        await conn.current?.startTalking()
        setMicBlocked(false)
      } catch {
        setTalking(false)
        setMicBlocked(true)
      }
    },
    stopTalking() {
      setTalking(false)
      conn.current?.stopTalking()
    },
    // A typed or tapped question (the example phrases on an empty job): the server only transcribes audio, so his
    // line is shown here.
    sendText(text: string) {
      setCaptions((lines) => addCaption(lines, { v: 1, type: 'caption', who: 'user', text, final: true }))
      conn.current?.sendText(text)
    },
    // He starts a photo himself; the server answers with the request to send it on.
    offerPhoto: () => conn.current?.mediaOffer('photo'),
    // A photo of his manual page or wiring sticker: read as a page and cited as "Photo of manual" (S7).
    offerManual: () => conn.current?.mediaOffer('document'),
    mediaReady: (requestId: string, uri: string, kind: MediaKind) => conn.current?.mediaReady(requestId, uri, kind),
    // Closing the sheet ends the request on the server too, so the tool answers the model.
    cancelMedia() {
      if (media.request) conn.current?.mediaCancel(media.request.request_id)
      setMedia(noMedia)
    },
    // His tap on the step card; the server hands out the next step or gate (ws-events step_done).
    stepDone: (n: number) => conn.current?.stepDone(n),
    playClip: async (url: string) => (await conn.current?.playClip(url)) ?? false,
    retry: () => setAttempt((n) => n + 1),
  }
}
