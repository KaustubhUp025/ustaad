import { Camera, Flashlight } from 'lucide-react'
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
export function CameraSheet({ view: { request, retakeReason }, title, jobId, onSent, onCancel }: Props) {
  const { t } = useTranslation()
  const camera = useCamera()
  const fallback = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<Phase>('ready')
  const [reasonShown, setReasonShown] = useState(retakeReason)
  if (retakeReason !== reasonShown) {
    setReasonShown(retakeReason)
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

  return (
    <section
      role="dialog"
      aria-labelledby="camera-title"
      className="mt-auto flex animate-in flex-col gap-4 rounded-t-xl bg-card px-4 pt-5 pb-6 shadow-lg slide-in-from-bottom motion-reduce:animate-none"
    >
      <h2 id="camera-title" className="font-heading text-[length:var(--text-lg)] leading-tight font-bold">
        {title}
      </h2>

      {/* Viewfinder: the live back camera when allowed, else a hint; the framing outline marks what should fill it. */}
      <div className="relative flex aspect-video items-end justify-center overflow-hidden rounded-lg bg-graphite text-center text-housing">
        <video ref={camera.video} muted playsInline aria-hidden className={live ? 'absolute inset-0 size-full object-cover' : 'hidden'} />
        {['top-3 left-3 border-t-4 border-l-4', 'top-3 right-3 border-t-4 border-r-4', 'bottom-3 left-3 border-b-4 border-l-4', 'right-3 bottom-3 border-r-4 border-b-4'].map(
          (corner) => (
            <span key={corner} aria-hidden className={`absolute size-8 border-primary ${corner}`} />
          ),
        )}
        {request.framing_tip && (
          <p className={live ? 'relative mb-4 bg-graphite/80 px-2 text-[length:var(--text-sm)]' : 'relative mb-auto mt-auto px-10 text-[length:var(--text-body)]'}>
            {request.framing_tip}
          </p>
        )}
        {camera.torch !== null && (
          <Button
            variant="outline"
            size="icon"
            aria-label={t('camera.flash')}
            aria-pressed={camera.torch}
            className="absolute top-3 right-14 size-(--touch) bg-graphite/80 text-housing"
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
      <Button
        className="h-(--touch) gap-2 text-[length:var(--text-body)]"
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
      <Button variant="outline" className="h-(--touch) text-[length:var(--text-body)]" disabled={busy} onClick={onCancel}>
        {t('camera.notNow')}
      </Button>
    </section>
  )
}
