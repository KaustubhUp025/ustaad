import { useEffect, useRef, useState } from 'react'

import { type LiveConnection, type LiveStatus, type ServerFrame, openLive } from './liveClient'

export type CaptionLine = { who: 'user' | 'ustaad'; text: string; final: boolean }
type CaptionFrame = Extract<ServerFrame, { type: 'caption' }>

const SHOWN = 3 // DESIGN.md: the last 3 turns stay on screen

// A partial caption replaces the previous partial from the same speaker; the final one locks it.
export function addCaption(lines: CaptionLine[], { who, text, final }: CaptionFrame): CaptionLine[] {
  const open = lines.findLastIndex((l) => l.who === who && !l.final)
  const next = open === -1 ? [...lines, { who, text, final }] : lines.with(open, { who, text, final })
  return next.slice(-SHOWN)
}

export function useLive(lang: string) {
  const [status, setStatus] = useState<LiveStatus>('connecting')
  const [captions, setCaptions] = useState<CaptionLine[]>([])
  const [talking, setTalking] = useState(false)
  const [micBlocked, setMicBlocked] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const conn = useRef<LiveConnection | null>(null)

  useEffect(() => {
    const c = openLive(
      lang,
      (frame) => {
        if (frame.type === 'caption') setCaptions((lines) => addCaption(lines, frame))
      },
      setStatus,
    )
    conn.current = c
    return () => c.close()
  }, [lang, attempt])

  return {
    status,
    captions,
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
    retry: () => setAttempt((n) => n + 1),
  }
}
