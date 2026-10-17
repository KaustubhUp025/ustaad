import { useEffect, useRef, useState } from 'react'

import { addCaption, type CaptionLine } from './captionHistory'
import { type LiveConnection, type LiveStatus, type MediaKind, openLive } from './liveClient'
import { mediaReducer, noMedia } from './media'
import { noQuotes, quotesReducer } from './quotes'
import { noRepair, repairReducer } from './safety'

export function useLive(lang: string, jobId: string) {
  const [status, setStatus] = useState<LiveStatus>('connecting')
  const [captions, setCaptions] = useState<CaptionLine[]>([])
  const [repair, setRepair] = useState(noRepair)
  const [media, setMedia] = useState(noMedia)
  const [quotes, setQuotes] = useState(noQuotes)
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
        setRepair((view) => repairReducer(view, frame))
        setMedia((view) => mediaReducer(view, frame))
        setQuotes((view) => quotesReducer(view, frame))
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
    retry: () => setAttempt((n) => n + 1),
  }
}
