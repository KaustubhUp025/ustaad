import { Mic } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { useLive } from '@/audio/useLive'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// The job screen, voice part (T11): live captions and the push-to-talk mic.
export default function Job() {
  const { t, i18n } = useTranslation()
  // ?lang= picks the language until onboarding (T21) saves it on the profile.
  const lang = useSearchParams()[0].get('lang') ?? i18n.language
  const live = useLive(lang)

  useEffect(() => {
    void i18n.changeLanguage(lang)
    document.documentElement.lang = lang
  }, [i18n, lang])

  const notice = { connecting: 'live.connecting', reconnecting: 'live.reconnecting', failed: 'live.failed', ready: null }[
    live.status
  ]

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="bg-graphite px-4 py-4 text-housing">
        <h1 className="font-heading text-[length:var(--text-xl)] font-bold">Ustaad</h1>
      </header>

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
        <p className="text-[length:var(--text-sm)] text-muted-foreground">{t(live.talking ? 'live.listening' : 'live.hold')}</p>
      </footer>
    </main>
  )
}
