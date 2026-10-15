// The in-page camera: a live back-camera viewfinder inside the sheet, so the page never leaves for the camera app
// (Android can kill a PWA in the background) and the framing outline sits over the real picture.
// 'unavailable' (no permission, no camera, old browser) falls back to the phone's own camera app.
import { useEffect, useRef, useState } from 'react'

type ImageCaptureLike = { takePhoto(): Promise<Blob> }
declare const ImageCapture: { new (track: MediaStreamTrack): ImageCaptureLike } | undefined

export function useCamera() {
  const video = useRef<HTMLVideoElement>(null)
  const track = useRef<MediaStreamTrack | null>(null)
  const [state, setState] = useState<'starting' | 'live' | 'unavailable'>('starting')
  const [torch, setTorch] = useState<boolean | null>(null) // null: this camera has no torch control

  useEffect(() => {
    let stream: MediaStream | null = null
    let stopped = false
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 } }, audio: false })
      .then(async (s) => {
        stream = s
        if (stopped) return s.getTracks().forEach((t) => t.stop())
        track.current = s.getVideoTracks()[0]
        const caps = track.current.getCapabilities?.() as { torch?: boolean } | undefined
        setTorch(caps?.torch ? false : null)
        video.current!.srcObject = s
        await video.current!.play()
        setState('live')
      })
      .catch(() => setState('unavailable')) ?? setState('unavailable')
    return () => {
      stopped = true
      stream?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  return {
    video,
    state,
    torch,
    async toggleTorch() {
      const on = !torch
      await track.current?.applyConstraints({ advanced: [{ torch: on } as MediaTrackConstraintSet] })
      setTorch(on)
    },
    // A full-resolution still where the browser can take one (Android Chrome), otherwise the current frame.
    async capture(): Promise<Blob> {
      if (typeof ImageCapture !== 'undefined' && track.current) {
        try {
          return await new ImageCapture(track.current).takePhoto()
        } catch {
          // some cameras refuse takePhoto while streaming; the frame below is the fallback
        }
      }
      const v = video.current!
      const canvas = new OffscreenCanvas(v.videoWidth, v.videoHeight)
      canvas.getContext('2d')!.drawImage(v, 0, 0)
      return canvas.convertToBlob({ type: 'image/jpeg', quality: 0.92 })
    },
  }
}
