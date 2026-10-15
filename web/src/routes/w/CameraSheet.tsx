import { Camera, Flashlight, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { uploadPhoto } from '@/api/media'
import type { MediaView } from '@/audio/media'
import { prepare } from '@/camera/photo'
import { useCamera } from '@/camera/useCamera'
import { Button } from '@/components/ui/button'

type Props = {
  view: MediaView & { request: NonNullable<MediaView['request']> }
  title: string
  jobId: string
  onSent: (uri: string) => void
  onCancel: () => void
}

type Phase = 'ready' | 'dark' | 'blurry' | 'sending' | 'checking' | 'failed'

// The camera sheet (DESIGN.md): Ustaad's request as the title and a framing outline over the live viewfinder.
// It takes the job's middle area and leaves the mic below it, so he can still talk to Ustaad. A very dark or blurry
// photo is caught on the phone before any upload; "send anyway" lets him overrule it. The parent keys the sheet by
// request, so the camera keeps running through retakes; a new retake reason resets the sheet.
export function CameraSheet({ view: { request, retakeReason, answers }, title, jobId, onSent, onCancel }: Props) {
  const { t } = useTranslation()
  const camera = useCamera()
  const fallback = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<Phase>('ready')
  // Each server answer unlocks the sheet, even a second retake with the same reason (found on the phone, Oct 15).
  const [answersSeen, setAnswersSeen] = useState(answers)
  if (answers !== answersSeen) {
    setAnswersSeen(answers)
    setPhase('ready')
  }
  const held = useRef<Blob | null>(null) // the photo the phone-side check rejected, for "send anyway"

  const upload = async (jpeg: Blob) => {
    setPhase('sending')
    try {
      onSent(await uploadPhoto(jpeg, jobId, request.request_id))
      setPhase('checking')
    } catch {
      setPhase('failed')
    }
  }

  const take = async (photo: Blob | undefined) => {
    if (!photo) return
    const { jpeg, problem } = await prepare(photo)
    held.current = jpeg
    if (problem) setPhase(problem)
    else await upload(jpeg)
  }

  const live = camera.state === 'live'
  // One button cycles the zoom steps the camera supports (1x, 2x, 4x), so it costs no extra row.
  const nextZoom = camera.zoomSteps[(camera.zoomSteps.indexOf(camera.zoom) + 1) % camera.zoomSteps.length] ?? 1
  const busy = phase === 'sending' || phase === 'checking'
  const message = {
    ready: retakeReason,
    dark: t('camera.dark'),
    blurry: t('camera.blurry'),
    sending: t('camera.sending'),
    checking: t('camera.checking'),
    failed: t('camera.failed'),
  }[phase]
  const warn = phase === 'dark' || phase === 'blurry' || phase === 'failed' || (phase === 'ready' && retakeReason)

  const controls = 'size-(--touch) rounded-full bg-graphite/80 text-housing hover:bg-graphite'

  return (
    <section
      role="dialog"
      aria-labelledby="camera-title"
      className="mt-auto flex animate-in flex-col gap-3 rounded-t-xl bg-card px-4 pt-4 pb-4 shadow-lg slide-in-from-bottom motion-reduce:animate-none"
    >
      {/* Everything fits above the mic on a 360 x 800 phone, so he can still talk while framing (phone test, Oct 15). */}
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <h2 id="camera-title" className="font-heading text-[length:var(--text-lg)] leading-tight font-bold">
            {title}
          </h2>
          {request.framing_tip && <p className="text-[length:var(--text-sm)] text-muted-foreground">{request.framing_tip}</p>}
        </div>
        <Button variant="ghost" size="icon" aria-label={t('camera.notNow')} className="size-(--touch) shrink-0" disabled={busy} onClick={onCancel}>
          <X aria-hidden className="size-6" />
        </Button>
      </div>

      {/* Viewfinder: the live back camera when allowed, else a hint; the framing outline marks what should fill it.
          Portrait like the photo it takes, so what he sees is what gets sent. Zoom and torch sit in the bottom
          corners, clear of the middle he is framing. */}
      <div className="relative mx-auto flex aspect-[3/4] h-[min(300px,36dvh)] items-center justify-center overflow-hidden rounded-lg bg-graphite text-center text-housing">
        <video ref={camera.video} muted playsInline aria-hidden className={live ? 'absolute inset-0 size-full object-cover' : 'hidden'} />
        {['top-3 left-3 border-t-4 border-l-4', 'top-3 right-3 border-t-4 border-r-4', 'bottom-3 left-3 border-b-4 border-l-4', 'right-3 bottom-3 border-r-4 border-b-4'].map(
          (corner) => (
            <span key={corner} aria-hidden className={`absolute size-8 border-primary ${corner}`} />
          ),
        )}
        {camera.zoomSteps.length > 0 && (
          <Button
            variant="ghost"
            aria-label={t('camera.zoom', { n: nextZoom })}
            className={`absolute bottom-2 left-2 ${controls} text-[length:var(--text-sm)] font-semibold`}
            onClick={() => void camera.setZoom(nextZoom)}
          >
            {camera.zoom}×
          </Button>
        )}
        {camera.torch !== null && (
          <Button
            variant="ghost"
            size="icon"
            aria-label={t('camera.flash')}
            aria-pressed={camera.torch}
            className={`absolute right-2 bottom-2 ${controls} ${camera.torch ? 'text-primary' : ''}`}
            onClick={() => void camera.toggleTorch()}
          >
            <Flashlight aria-hidden className="size-6" />
          </Button>
        )}
      </div>

      {message && (
        <p
          role={warn ? 'alert' : 'status'}
          className={warn ? 'border-l-4 border-destructive pl-3 text-[length:var(--text-body)]' : 'text-[length:var(--text-body)]'}
        >
          {message}
        </p>
      )}

      <input
        ref={fallback}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          void take(e.target.files?.[0])
          e.target.value = ''
        }}
      />
      <div className="flex gap-2">
        <Button
          className="h-(--touch) flex-1 gap-2 text-[length:var(--text-body)]"
          disabled={busy || camera.state === 'starting'}
          onClick={() => (live ? void camera.capture().then(take) : fallback.current?.click())}
        >
          <Camera aria-hidden className="size-6" />
          {t(phase === 'ready' && !retakeReason ? 'camera.take' : 'camera.retake')}
        </Button>
        {(phase === 'dark' || phase === 'blurry') && (
          <Button variant="outline" className="h-(--touch) text-[length:var(--text-body)]" onClick={() => void upload(held.current!)}>
            {t('camera.sendAnyway')}
          </Button>
        )}
      </div>
    </section>
  )
}
