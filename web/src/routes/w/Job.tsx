import { BookOpen, Camera, Check, CircleCheck, Mic, ShieldAlert, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { demoSession } from '@/api/session'
import gateClips from '@/audio/gateClips.json'
import { hasProfile } from '@/audio/profile'
import { stepLines } from '@/audio/safety'
import { speak } from '@/audio/speak'
import { useLive } from '@/audio/useLive'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { CameraSheet } from './CameraSheet'
import { CodeReadout } from './CodeReadout'
import { ProfileCard } from './ProfileCard'
import { SourceChip } from './SourceChip'
import { QuotesCard } from './QuotesCard'
import { StatusPill, WorkerHeader } from './WorkerHeader'

// The job screen: live captions, the current step card, the safety gate and stop screens, the camera sheet, and the
// push-to-talk mic.
// Without a demo session there is no token for the voice line, so he starts one from Home (mock replays need none).
export default function Job() {
  if (import.meta.env.VITE_MOCK_LIVE !== '1' && !demoSession()) return <Navigate to="/w" replace />
  return <JobScreen />
}

function JobScreen() {
  const { t, i18n } = useTranslation()
  // ?lang= picks the language until onboarding (T21) saves it on the profile.
  const [params] = useSearchParams()
  const lang = params.get('lang') ?? i18n.language
  // Home's "Set up a profile": the empty screen explains the interview instead of offering repair questions.
  const onboarding = params.get('onboarding') === '1'
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const live = useLive(lang, id)
  const { step, gate, failReason, stop, closed } = live.repair
  const lines = step && stepLines(step)
  const { request } = live.media
  // While a gate shows, he first reads what to switch off; the gate's photo button then opens the sheet.
  const [gatePhoto, setGatePhoto] = useState(false)
  const [shownGate, setShownGate] = useState(gate?.gate_id)
  if (gate?.gate_id !== shownGate) {
    setShownGate(gate?.gate_id)
    setGatePhoto(false)
  }
  const sheet = request && (!gate || gatePhoto)
  // One tap per step: the button waits for the next card, so a double tap cannot skip a step.
  const [tappedStep, setTappedStep] = useState<number | null>(null)

  useEffect(() => {
    void i18n.changeLanguage(lang)
    document.documentElement.lang = lang
  }, [i18n, lang])

  // The gate's fixed text, played once when it opens and again on "Hear it again": the recorded clip through Ustaad's
  // speaker (`make gate-clips`), or the browser voice where there is no clip (see audio/speak.ts).
  const gateText = gate ? `${t(`repair.gate.${gate.gate_id}`)} ${t(`repair.evidence.${gate.gate_id}`)}` : ''
  const sayGate = async () => {
    if (!gate) return
    const hasClip = lang in gateClips
    if (!(hasClip && (await live.playClip(`/audio/gates/${lang}/${gate.gate_id}.pcm`)))) speak(gateText, lang)
  }
  useEffect(() => {
    if (gateText) void sayGate()
    // Only a new gate (or language) plays it again; sayGate changes every render.
  }, [gateText, lang])

  // Connecting shows in the header's pill; the strip below is for states he has to act on.
  const notice = {
    connecting: null,
    reconnecting: 'live.reconnecting',
    failed: 'live.failed',
    busy: 'live.busy',
    ready: null,
  }[live.status]

  return (
    <main className={cn('mx-auto flex min-h-dvh max-w-2xl flex-col', stop && 'bg-destructive text-housing')}>
      {!stop && (
        <>
          <WorkerHeader back>
            <StatusPill
              state={live.status === 'ready' ? 'ok' : live.status === 'connecting' || live.status === 'reconnecting' ? 'pending' : 'error'}
              label={t(live.status === 'ready' ? 'health.live' : live.status === 'connecting' ? 'health.checking' : 'health.offline')}
            />
          </WorkerHeader>
          {live.identified && <CodeReadout identified={live.identified} />}
        </>
      )}

      {notice && (
        <div role="status" className="flex flex-col items-start gap-3 border-b border-border px-4 py-3">
          <p>{t(notice)}</p>
          {(live.status === 'failed' || live.status === 'busy') && (
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
      ) : sheet ? (
        <CameraSheet
          key={request.request_id}
          view={{ ...live.media, request }}
          title={gate ? t(`repair.evidence.${gate.gate_id}`) : request.target || t(request.kind === 'document' ? 'camera.manualTitle' : 'camera.ownTitle')}
          gateId={gate?.gate_id}
          jobId={id}
          onSent={(uri) => live.mediaReady(request.request_id, uri, request.kind)}
          // A gate's photo request belongs to the gate: closing the sheet goes back to the gate screen.
          onCancel={gate ? () => setGatePhoto(false) : live.cancelMedia}
        />
      ) : gate ? (
        <section role="alert" className="flex flex-1 flex-col justify-center gap-5 bg-graphite px-6 py-8 text-housing">
          <div className="flex items-center gap-3">
            <ShieldAlert aria-hidden className="size-10 shrink-0 text-primary" />
            <h2 className="font-heading text-[length:var(--text-xl)] leading-tight font-bold text-primary">{t('repair.gateTitle')}</h2>
          </div>
          <p className="text-[length:var(--text-lg)] font-semibold">{t(`repair.gate.${gate.gate_id}`)}</p>
          <p className="text-[length:var(--text-body)]">{t(`repair.evidence.${gate.gate_id}`)}</p>
          <p className="border-l-2 border-housing/40 pl-3 text-[length:var(--text-sm)] text-housing/80">
            {t('repair.gateWhy')} {t('repair.gateNext')}
          </p>
          {failReason && (
            <p className="border-l-4 border-primary pl-3 text-[length:var(--text-body)]">
              {t('repair.gateFailed', { reason: failReason })}
            </p>
          )}
          {/* The server opens the gate's photo request with the gate; if it has not arrived, the offer fetches it. */}
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              className="h-14 gap-2 px-6 text-[length:var(--text-body)] font-semibold sm:flex-1"
              disabled={live.status !== 'ready'}
              onClick={() => {
                setGatePhoto(true)
                if (!request) live.offerPhoto()
              }}
            >
              <Camera aria-hidden className="size-6" />
              {t('camera.sendGatePhoto')}
            </Button>
            <Button
              variant="outline"
              className="h-14 gap-2 border-housing/40 bg-transparent px-6 text-[length:var(--text-body)] text-housing hover:bg-housing/10 hover:text-housing"
              onClick={() => void sayGate()}
            >
              <Volume2 aria-hidden className="size-6" />
              {t('repair.hearAgain')}
            </Button>
          </div>
        </section>
      ) : (
        <>
          {step && (
            // A service tag: 4px radius and one punched-hole notch at the left (DESIGN.md).
            <article className="relative mx-4 mt-4 rounded-sm border border-border bg-card px-5 py-3">
              <span aria-hidden className="absolute top-1/2 -left-1.5 size-3 -translate-y-1/2 rounded-full border border-border bg-background" />
              <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('repair.step', { n: step.n, of: step.of })}</p>
              <div className="text-[length:var(--text-sm)] text-muted-foreground">
                <SourceChip
                  kind={step.source.kind}
                  label={step.source.kind === 'manual_photo' ? t('repair.source.manualPhoto') : step.source.label}
                  audioUri={step.source.audio_uri}
                />
                {lines?.original && <p>{lines.original}</p>}
              </div>
              <p className="text-[length:var(--text-caption)]">{lines?.main}</p>
              <Button
                className="mt-3 h-(--touch) w-full gap-2 text-[length:var(--text-body)]"
                disabled={live.status !== 'ready' || tappedStep === step.n}
                onClick={() => {
                  setTappedStep(step.n)
                  live.stepDone(step.n)
                }}
              >
                <Check aria-hidden className="size-6" />
                {t('repair.stepDone')}
              </Button>
            </article>
          )}
          <section aria-live="polite" className="flex flex-1 flex-col gap-3 px-4 py-5 text-[length:var(--text-caption)]">
            {live.captions.length === 0 && !step && !closed && (
              // The empty job explains itself: what to do, questions to tap (not while onboarding), and the photo buttons below.
              <div className="flex flex-1 flex-col justify-center gap-5">
                <div className="flex items-start gap-3">
                  <span aria-hidden className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <Mic className="size-6" />
                  </span>
                  <div>
                    <h2 className="font-heading text-[length:var(--text-lg)] leading-tight font-bold">
                      {t(onboarding ? 'onboard.jobTitle' : 'live.emptyTitle')}
                    </h2>
                    <p className="mt-1 text-[length:var(--text-body)] text-muted-foreground">
                      {t(onboarding ? 'onboard.jobText' : 'live.emptyText')}
                    </p>
                  </div>
                </div>
                {!onboarding && (
                  <>
                    <div className="flex flex-col gap-2">
                      <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('live.tapToAsk')}</p>
                      {(['ex1', 'ex2', 'ex3'] as const).map((key) => (
                        <button
                          key={key}
                          type="button"
                          lang="hi"
                          disabled={live.status !== 'ready'}
                          onClick={() => live.sendText(t(`live.${key}`))}
                          className="min-h-(--touch) rounded-lg border border-border bg-card px-4 py-3 text-left text-[length:var(--text-body)] outline-none hover:border-primary focus-visible:ring-4 focus-visible:ring-ring disabled:opacity-50"
                        >
                          “{t(`live.${key}`)}”
                        </button>
                      ))}
                    </div>
                    <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('live.orShow')}</p>
                  </>
                )}
              </div>
            )}
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

          {closed && (
            <section role="status" className="mx-4 flex flex-col gap-3 rounded-lg border border-ok bg-card px-4 py-4">
              <div className="flex items-center gap-3">
                <CircleCheck aria-hidden className="size-8 shrink-0 text-ok" />
                <div>
                  <h2 className="font-heading text-[length:var(--text-lg)] font-bold">{t('repair.closedTitle')}</h2>
                  <p className="text-[length:var(--text-body)] text-muted-foreground">{t('repair.closed')}</p>
                </div>
              </div>
              <div className="flex gap-3">
                <Button
                  className="h-(--touch) flex-1 text-[length:var(--text-body)]"
                  onClick={() => navigate(`/w/job/j_${crypto.randomUUID().slice(0, 8)}?lang=${lang}`)}
                >
                  {t('repair.newJob')}
                </Button>
                <Button asChild variant="outline" className="h-(--touch) px-6 text-[length:var(--text-body)]">
                  <Link to="/w">{t('repair.home')}</Link>
                </Button>
              </div>
            </section>
          )}

          {hasProfile(live.profile) && <ProfileCard profile={live.profile} />}
          <QuotesCard quoteRequestId={live.quotes.quoteRequestId} initialItems={live.quotes.items} />
        </>
      )}

      <footer className="flex flex-col items-center gap-2 px-4 pt-2 pb-6">
        {live.micBlocked && <p role="alert">{t('live.micBlocked')}</p>}
        {/* Mic in the middle; beside it he can show Ustaad something himself. The mic stays the main action. */}
        <div className="grid w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
          {!stop && !gate && !request ? (
            <Button
              variant="outline"
              className="h-auto min-h-(--touch) flex-col gap-0.5 justify-self-start px-3 py-1 text-[length:var(--text-sm)]"
              disabled={live.status !== 'ready'}
              onClick={live.offerPhoto}
            >
              <Camera aria-hidden className="size-6" />
              {t('camera.sendGatePhoto')}
            </Button>
          ) : (
            <span />
          )}
        <button
          type="button"
          aria-pressed={live.talking}
          aria-label={t('live.hold')}
          // While reconnecting he can already talk: the turn is held and sent once the new session is ready (T27).
          disabled={live.status !== 'ready' && live.status !== 'reconnecting'}
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
          {!stop && !gate && !request ? (
            <Button
              variant="outline"
              className="h-auto min-h-(--touch) flex-col gap-0.5 justify-self-end px-3 py-1 text-[length:var(--text-sm)]"
              disabled={live.status !== 'ready'}
              onClick={live.offerManual}
            >
              <BookOpen aria-hidden className="size-6" />
              {t('camera.manualPhoto')}
            </Button>
          ) : (
            <span />
          )}
        </div>
        <p className={cn('text-[length:var(--text-sm)]', !stop && 'text-muted-foreground')}>
          {t(live.talking ? 'live.listening' : 'live.hold')}
        </p>
      </footer>
    </main>
  )
}
