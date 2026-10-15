// What the camera sheet shows (BUILD-GUIDE T17): the open media request and, after a poor photo, why to retake.
// A retake stays on the same request ID; a result with no retake reason closes the sheet. `answers` counts the
// server's answers for the request, so the sheet unlocks on each one, even when two retakes give the same reason.
import type { ServerFrame } from './liveClient'

type Of<T extends ServerFrame['type']> = Extract<ServerFrame, { type: T }>

export type MediaView = { request: Of<'media_request'> | null; retakeReason: string | null; answers: number }

export const noMedia: MediaView = { request: null, retakeReason: null, answers: 0 }

export function mediaReducer(view: MediaView, frame: ServerFrame): MediaView {
  // After a reconnect the server sends the job's open requests again, so the sheet never waits on a dead request.
  if (frame.type === 'session_ready') return noMedia
  if (frame.type === 'media_request') return { request: frame, retakeReason: null, answers: 0 }
  if (frame.type !== 'media_result' || frame.request_id !== view.request?.request_id) return view
  return frame.retake_reason ? { ...view, retakeReason: frame.retake_reason, answers: view.answers + 1 } : noMedia
}
