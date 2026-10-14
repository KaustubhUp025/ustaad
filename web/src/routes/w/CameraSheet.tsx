import { Camera } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { uploadPhoto } from '@/api/media'
import type { MediaView } from '@/audio/media'
import { Button } from '@/components/ui/button'

type Props = {
  view: MediaView & { request: NonNullable<MediaView['request']> }
  jobId: string
  onSent: (uri: string) => void
  onCancel: () => void
}

// The camera sheet (DESIGN.md): slides up over the job with Ustaad's request as the title and a framing outline.
// It takes the job's middle area and leaves the mic below it, so he can still talk to Ustaad. The parent keys it by request and retake, so
// each retake starts fresh.
export function CameraSheet({ view: { request, retakeReason }, jobId, onSent, onCancel }: Props) {
  const { t } = useTranslation()
  const input = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<'ready' | 'sending' | 'checking' | 'failed'>('ready')

  const send = async (file: File | undefined) => {
    if (!file) return
    setPhase('sending')
    try {
      onSent(await uploadPhoto(file, jobId, request.request_id))
      setPhase('checking')
    } catch {
      setPhase('failed')
    }
  }

  const busy = phase === 'sending' || phase === 'checking'
  const status = { ready: null, sending: 'camera.sending', checking: 'camera.checking', failed: 'camera.failed' }[phase]

  return (
    <section
      role="dialog"
      aria-labelledby="camera-title"
      className="mt-auto flex animate-in flex-col gap-4 rounded-t-xl bg-card px-4 pt-5 pb-6 shadow-lg slide-in-from-bottom motion-reduce:animate-none"
    >
      <h2 id="camera-title" className="font-heading text-[length:var(--text-lg)] leading-tight font-bold">
        {request.target}
      </h2>

      {/* Viewfinder hint: the framing outline marks what should fill the photo. */}
      <div className="relative flex aspect-video items-center justify-center rounded-lg bg-graphite px-10 text-center text-housing">
        {['top-3 left-3 border-t-4 border-l-4', 'top-3 right-3 border-t-4 border-r-4', 'bottom-3 left-3 border-b-4 border-l-4', 'right-3 bottom-3 border-r-4 border-b-4'].map(
          (corner) => (
            <span key={corner} aria-hidden className={`absolute size-8 border-primary ${corner}`} />
          ),
        )}
        <p className="text-[length:var(--text-body)]">{request.framing_tip}</p>
      </div>

      {retakeReason && phase === 'ready' && (
        <p role="alert" className="border-l-4 border-destructive pl-3 text-[length:var(--text-body)]">
          {retakeReason}
        </p>
      )}
      {status && (
        <p role="status" className="text-[length:var(--text-body)]">
          {t(status)}
        </p>
      )}

      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          void send(e.target.files?.[0])
          e.target.value = ''
        }}
      />
      <Button
        className="h-(--touch) gap-2 text-[length:var(--text-body)]"
        disabled={busy}
        onClick={() => input.current?.click()}
      >
        <Camera aria-hidden className="size-6" />
        {t(retakeReason || phase === 'failed' ? 'camera.retake' : 'camera.take')}
      </Button>
      <Button variant="outline" className="h-(--touch) text-[length:var(--text-body)]" disabled={busy} onClick={onCancel}>
        {t('camera.notNow')}
      </Button>
    </section>
  )
}
