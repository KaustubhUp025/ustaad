import { Pause, Play } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { voiceNoteUrl } from '@/api/media'
import { demoSession } from '@/api/session'
import { cn } from '@/lib/utils'

type Props = { kind: string; label: string; audioUri: string | null }

// The step's source (DESIGN.md: "[▶ Ramesh · May 2025]"). With a voice note he can hear the senior's original words;
// without one it is just the label. General guidance has no verified source, so it gets its own outline and never a
// play button (SPEC §6 source tiers).
export function SourceChip({ kind, label, audioUri }: Props) {
  const { t } = useTranslation()
  const [state, setState] = useState<'idle' | 'loading' | 'playing' | 'failed'>('idle')
  const audio = useRef<HTMLAudioElement | null>(null)
  useEffect(() => () => audio.current?.pause(), [])

  if (kind === 'general') {
    return (
      <span className="inline-flex items-center rounded-sm border-2 border-dashed border-muted-foreground px-3 py-1 text-foreground">
        {t('repair.source.general')}
      </span>
    )
  }
  if (!audioUri) return <span>{label}</span>

  const toggle = async () => {
    if (state === 'playing') {
      audio.current?.pause()
      return setState('idle')
    }
    setState('loading')
    try {
      // A signed URL lasts 900 s, so it is fetched on each play rather than kept.
      audio.current ??= new Audio()
      audio.current.src = await voiceNoteUrl(audioUri, demoSession()?.token ?? '')
      audio.current.onended = () => setState('idle')
      await audio.current.play()
      setState('playing')
    } catch {
      setState('failed')
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        aria-label={t(state === 'playing' ? 'repair.source.stop' : 'repair.source.play', { label })}
        aria-pressed={state === 'playing'}
        disabled={state === 'loading'}
        onClick={() => void toggle()}
        className={cn(
          'inline-flex min-h-(--touch) items-center gap-2 rounded-sm border-2 border-ok px-3 text-ok',
          'outline-none focus-visible:ring-4 focus-visible:ring-ring disabled:opacity-60',
        )}
      >
        {state === 'playing' ? <Pause aria-hidden className="size-5" /> : <Play aria-hidden className="size-5" />}
        {label}
      </button>
      {state === 'failed' && <span role="alert">{t('repair.source.failed')}</span>}
    </span>
  )
}
