// What the camera sheet shows (BUILD-GUIDE T17): the open media request and, after a poor photo, why to retake.
// A retake stays on the same request ID; a result with no retake reason closes the sheet.
import type { ServerFrame } from './liveClient'

type Of<T extends ServerFrame['type']> = Extract<ServerFrame, { type: T }>

export type MediaView = { request: Of<'media_request'> | null; retakeReason: string | null }

export const noMedia: MediaView = { request: null, retakeReason: null }

export function mediaReducer(view: MediaView, frame: ServerFrame): MediaView {
  if (frame.type === 'media_request') return { request: frame, retakeReason: null }
  if (frame.type !== 'media_result' || frame.request_id !== view.request?.request_id) return view
  return frame.retake_reason ? { ...view, retakeReason: frame.retake_reason } : noMedia
}
