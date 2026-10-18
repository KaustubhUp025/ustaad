import { Camera, Check, Flashlight, ImageUp, LoaderCircle, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { uploadPhoto } from '@/api/media'
import type { MediaView } from '@/audio/media'
import { tryPrepare } from '@/camera/photo'
import { samplesFor } from '@/camera/samples'
import { useCamera } from '@/camera/useCamera'
import { Button } from '@/components/ui/button'

type Props = {
  view: MediaView & { request: NonNullable<MediaView['request']> }
  title: string
  gateId?: string
  jobId: string
  onSent: (uri: string) => void
  onCancel: () => void
}

type Phase = 'ready' | 'dark' | 'blurry' | 'sending' | 'checking' | 'failed'

// Checks usually take 5-6 s, but about 1 in 4 took ~30 s (Oct 15); past this he is told it is still going.
const STILL_CHECKING_MS = 10_000

// The camera sheet (DESIGN.md): Ustaad's request as the title and a framing outline over the live viewfinder.
// It takes the job's middle area and leaves the mic below it, so he can still talk to Ustaad. A very dark or blurry
// photo is caught on the phone before any upload; "send anyway" lets him overrule it. The parent keys the sheet by
// request, so the camera keeps running through retakes; a new retake reason resets the sheet.
export function CameraSheet({ view: { request, retakeReason, answers }, title, gateId, jobId, onSent, onCancel }: Props) {
  const { t } = useTranslation()
  const samples = samplesFor(gateId)
  const camera = useCamera()
  const fallback = useRef<HTMLInputElement>(null)
  const picker = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<Phase>('ready')
  // Each server answer unlocks the sheet, even a second retake with the same reason (found on the phone, Oct 15).
  const [answersSeen, setAnswersSeen] = useState(answers)
  if (answers !== answersSeen) {
    setAnswersSeen(answers)
    setPhase('ready')
  }
  const held = useRef<Blob | null>(null) // the photo the phone-side check rejected, for "send anyway"
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (phase !== 'checking') return
    const timer = window.setTimeout(() => setSlow(true), STILL_CHECKING_MS)
    return () => {
      window.clearTimeout(timer)
      setSlow(false)
    }
  }, [phase])

  // While it is checked he sees the photo he sent under a scan line, not a live camera that looks like nothing is
  // happening (phone test, Oct 17: 4-5 s felt broken).
  const [sent, setSent] = useState<string | null>(null)
  useEffect(() => () => void (sent && URL.revokeObjectURL(sent)), [sent])

  const upload = async (jpeg: Blob) => {
    setSent(URL.createObjectURL(jpeg))
    setPhase('sending')
    try {
      onSent(await uploadPhoto(jpeg, jobId, request.request_id))
      setPhase('checking')
    } catch {
      setPhase('failed')
    }
  }

  // A sample goes as it is: the phone-side check is skipped, so the server judges it exactly as recorded.
  const sendSample = async (src: string) => {
    setPhase('sending')
    try {
      await upload(await (await fetch(src)).blob())
    } catch {
      setPhase('failed')
    }
  }

  const take = async (photo: Blob | undefined) => {
    if (!photo) return
    const prepared = await tryPrepare(photo)
    if (!prepared) {
      setPhase('failed')
      return
    }
    const { jpeg, problem } = prepared
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
    checking: t(slow ? 'camera.stillChecking' : 'camera.checking'),
    failed: t('camera.failed'),
  }[phase]
  const warn = phase === 'dark' || phase === 'blurry' || phase === 'failed' || (phase === 'ready' && retakeReason)

  const controls = 'size-(--touch) rounded-full bg-graphite/80 text-housing hover:bg-graphite'

  return (
    <section
      role="dialog"
      aria-labelledby="camera-title"
      className="mt-3 flex min-h-0 flex-1 flex-col gap-3 rounded-t-(--radius-sheet-top) border border-border bg-card px-4 pt-4 pb-4 shadow-lg motion-safe:animate-in motion-safe:slide-in-from-bottom motion-reduce:animate-none"
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
      {/* The viewfinder takes all the height the sheet has left (the phone test showed an empty band above it). */}
      <div className="relative min-h-[240px] flex-1">
      <div className="absolute inset-y-0 left-1/2 flex aspect-[3/4] h-full max-w-full -translate-x-1/2 items-center justify-center overflow-hidden rounded-lg bg-graphite text-center text-housing">
        <video ref={camera.video} muted playsInline aria-hidden className={live ? 'absolute inset-0 size-full object-cover' : 'hidden'} />
        {busy && sent && (
          <>
            <img src={sent} alt="" className="absolute inset-0 size-full object-cover" />
            <span aria-hidden className="absolute inset-x-0 h-1 animate-scan bg-primary motion-reduce:hidden" />
          </>
        )}
        {['top-3 left-3 border-t-4 border-l-4', 'top-3 right-3 border-t-4 border-r-4', 'bottom-16 left-3 border-b-4 border-l-4', 'right-3 bottom-16 border-r-4 border-b-4'].map(
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
      </div>

      {busy ? (
        <ol role="status" className="flex flex-col gap-1 text-[length:var(--text-body)]">
          <li className="flex items-center gap-2">
            {phase === 'sending' ? <LoaderCircle aria-hidden className="size-5 animate-spin motion-reduce:animate-none" /> : <Check aria-hidden className="size-5 text-ok" />}
            {t(phase === 'sending' ? 'camera.sending' : 'camera.sent')}
          </li>
          {phase === 'checking' && (
            <li className="flex items-center gap-2">
              <LoaderCircle aria-hidden className="size-5 animate-spin motion-reduce:animate-none" />
              {message}
            </li>
          )}
        </ol>
      ) : message && (
        <p
          role={warn ? 'alert' : 'status'}
          className={warn ? 'border-l-4 border-destructive pl-3 text-[length:var(--text-body)]' : 'text-[length:var(--text-body)]'}
        >
          {message}
        </p>
      )}

      {!busy && samples.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('samples.title')}</p>
          <ul className="grid grid-cols-3 gap-3">
            {samples.map((sample) => (
              <li key={sample.src} className="flex min-w-0 flex-col gap-1">
                <button
                  type="button"
                  className="aspect-square w-full overflow-hidden rounded-sm border border-border outline-none focus-visible:ring-4 focus-visible:ring-ring"
                  aria-label={t('samples.send', { name: t(sample.name) })}
                  onClick={() => void sendSample(sample.src)}
                >
                  <img src={sample.src} alt="" className="size-full object-cover" />
                </button>
                <span className="break-words text-[length:var(--text-sm)] leading-tight text-muted-foreground">
                  {t(`samples.${sample.provenance}`)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* A photo or screenshot already on the phone (a manual page, a sticker, an earlier job). Never at a gate:
          an old photo cannot show the power is off now. */}
      <input
        ref={picker}
        type="file"
        accept="image/*"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          void take(e.target.files?.[0])
          e.target.value = ''
        }}
      />
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
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          className="h-(--touch) w-full gap-2 text-[length:var(--text-body)] sm:flex-1"
          disabled={busy || camera.state === 'starting'}
          onClick={() => (live ? void camera.capture().then(take) : fallback.current?.click())}
        >
          <Camera aria-hidden className="size-6" />
          {t(phase === 'ready' && !retakeReason ? 'camera.take' : 'camera.retake')}
        </Button>
        {!gateId && phase !== 'dark' && phase !== 'blurry' && (
          <Button
            variant="outline"
            className="h-(--touch) w-full gap-2 text-[length:var(--text-body)] sm:w-auto"
            disabled={busy}
            onClick={() => picker.current?.click()}
          >
            <ImageUp aria-hidden className="size-6" />
            {t('camera.pickFromPhone')}
          </Button>
        )}
        {(phase === 'dark' || phase === 'blurry') && (
          <Button variant="outline" className="h-(--touch) w-full text-[length:var(--text-body)] sm:w-auto" onClick={() => void upload(held.current!)}>
            {t('camera.sendAnyway')}
          </Button>
        )}
      </div>
    </section>
  )
}
