import { Camera, Mic } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useSearchParams } from 'react-router-dom'

import { useLive } from '@/audio/useLive'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { CameraSheet } from './CameraSheet'

// The job screen: live captions, the current step card, the safety gate and stop screens, the camera sheet, and the
// push-to-talk mic.
export default function Job() {
  const { t, i18n } = useTranslation()
  // ?lang= picks the language until onboarding (T21) saves it on the profile.
  const lang = useSearchParams()[0].get('lang') ?? i18n.language
  const { id = '' } = useParams()
  const live = useLive(lang, id)
  const { step, gate, failReason, stop } = live.repair
  const { request } = live.media

  useEffect(() => {
    void i18n.changeLanguage(lang)
    document.documentElement.lang = lang
  }, [i18n, lang])

  const notice = { connecting: 'live.connecting', reconnecting: 'live.reconnecting', failed: 'live.failed', ready: null }[
    live.status
  ]

  return (
    <main className={cn('mx-auto flex min-h-dvh max-w-md flex-col', stop && 'bg-destructive text-housing')}>
      {!stop && (
        <header className="bg-graphite px-4 py-4 text-housing">
          <h1 className="font-heading text-[length:var(--text-xl)] font-bold">Ustaad</h1>
        </header>
      )}

      {notice && (
        <div role="status" className="flex flex-col items-start gap-3 border-b border-border px-4 py-3">
          <p>{t(notice)}</p>
          {live.status === 'failed' && (
            <Button variant="outline" className="h-(--touch) px-6 text-[length:var(--text-body)]" onClick={live.retry}>
              {t('live.retry')}
            </Button>
          )}
        </div>
      )}

      {stop ? (
        // SAFETY.md: the whole screen turns Fault Red with one fixed sentence for the reason; no audio.
        <section role="alert" className="flex flex-1 items-center px-6 py-10">
          <p className="text-[length:var(--text-lg)] font-semibold">{t([`repair.stop.${stop.reason}`, 'repair.stop.other'])}</p>
        </section>
      ) : request ? (
        <CameraSheet
          key={request.request_id}
          view={{ ...live.media, request }}
          jobId={id}
          onSent={(uri) => live.mediaReady(request.request_id, uri, request.kind)}
          onCancel={live.cancelMedia}
        />
      ) : gate ? (
        <section role="alert" className="flex flex-1 flex-col justify-center gap-4 bg-graphite px-6 py-10 text-housing">
          <h2 className="font-heading text-[length:var(--text-xl)] font-bold text-primary">{t('repair.gateTitle')}</h2>
          <p className="text-[length:var(--text-lg)]">{t(`repair.gate.${gate.gate_id}`)}</p>
          <p className="text-[length:var(--text-body)]">{t(`repair.evidence.${gate.gate_id}`)}</p>
          {failReason && (
            <p className="border-l-4 border-primary pl-3 text-[length:var(--text-body)]">
              {t('repair.gateFailed', { reason: failReason })}
            </p>
          )}
          {/* A gate photo must come from a server-issued request, so the button asks Ustaad for one; the
              media_request it sends opens the camera sheet. */}
          <Button
            className="h-(--touch) gap-2 self-start px-6 text-[length:var(--text-body)]"
            disabled={live.status !== 'ready'}
            onClick={() => live.say(t('camera.askGatePhoto'))}
          >
            <Camera aria-hidden className="size-6" />
            {t('camera.sendGatePhoto')}
          </Button>
        </section>
      ) : (
        <>
          <section aria-live="polite" className="flex flex-1 flex-col justify-end gap-3 px-4 py-6 text-[length:var(--text-caption)]">
            {live.captions.length === 0 && <p className="text-muted-foreground">{t('live.empty')}</p>}
            {live.captions.map((line, i) => (
              <p
                key={i}
                className={cn(
                  line.who === 'user' && 'ml-6 border-l-2 border-ok pl-3',
                  !line.final && 'text-muted-foreground',
                )}
              >
                <span className="sr-only">{t(line.who === 'user' ? 'live.you' : 'live.ustaad')}: </span>
                {line.text}
              </p>
            ))}
          </section>

          {step && (
            // A service tag: 4px radius and one punched-hole notch at the left (DESIGN.md).
            <article className="relative mx-4 rounded-sm border border-border bg-card px-5 py-3">
              <span aria-hidden className="absolute top-1/2 -left-1.5 size-3 -translate-y-1/2 rounded-full border border-border bg-background" />
              <p className="text-[length:var(--text-sm)] text-muted-foreground">
                {t('repair.step', { n: step.n, of: step.of })} · {step.source.label}
              </p>
              <p className="text-[length:var(--text-caption)]">{step.instruction}</p>
            </article>
          )}
        </>
      )}

      <footer className="flex flex-col items-center gap-2 px-4 pt-2 pb-6">
        {live.micBlocked && <p role="alert">{t('live.micBlocked')}</p>}
        <button
          type="button"
          aria-pressed={live.talking}
          aria-label={t('live.hold')}
          disabled={live.status !== 'ready'}
          className={cn(
            'flex size-(--mic) touch-none items-center justify-center rounded-full bg-primary text-primary-foreground select-none',
            'outline-none focus-visible:ring-4 focus-visible:ring-ring disabled:opacity-50',
            live.talking && 'ring-4 ring-graphite ring-offset-4 ring-offset-background',
          )}
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture(e.pointerId)
            void live.startTalking()
          }}
          onPointerUp={live.stopTalking}
          onPointerCancel={live.stopTalking}
          onKeyDown={(e) => {
            if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
              e.preventDefault()
              void live.startTalking()
            }
          }}
          onKeyUp={(e) => {
            if (e.key === ' ' || e.key === 'Enter') live.stopTalking()
          }}
          onContextMenu={(e) => e.preventDefault()}
        >
          <Mic aria-hidden className="size-9" />
        </button>
        <p className={cn('text-[length:var(--text-sm)]', !stop && 'text-muted-foreground')}>
          {t(live.talking ? 'live.listening' : 'live.hold')}
        </p>
      </footer>
    </main>
  )
}
