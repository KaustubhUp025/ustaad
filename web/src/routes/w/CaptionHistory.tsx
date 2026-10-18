import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { CaptionLine } from '@/audio/captionHistory'
import { cn } from '@/lib/utils'

import { isNearCaptionBottom } from './captionScroll'

type Props = { captions: CaptionLine[] }

export function CaptionHistory({ captions }: Props) {
  const { t } = useTranslation()
  const area = useRef<HTMLDivElement>(null)
  const [followLatest, setFollowLatest] = useState(true)

  useEffect(() => {
    if (followLatest) area.current?.scrollTo({ top: area.current.scrollHeight })
  }, [captions, followLatest])

  return (
    <section aria-labelledby="conversation-title" className="flex min-h-0 flex-1 flex-col justify-end px-4 py-6">
      <h2 id="conversation-title" className="sr-only">{t('live.conversation')}</h2>
      <div
        ref={area}
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        tabIndex={0}
        className="mt-auto max-h-[min(40dvh,20rem)] overflow-y-auto overscroll-contain pr-1 text-[length:var(--text-caption)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring"
        onScroll={(event) => setFollowLatest(isNearCaptionBottom(event.currentTarget))}
      >
        <div className="flex flex-col gap-3">
          {captions.length === 0 && <p className="text-muted-foreground">{t('live.empty')}</p>}
          {captions.map((line) => (
            <p
              key={line.id}
              className={cn(
                line.who === 'user' && 'ml-6 border-l-2 border-ok pl-3',
                !line.final && 'text-muted-foreground',
              )}
            >
              <span className="sr-only">{t(line.who === 'user' ? 'live.you' : 'live.ustaad')}: </span>
              {line.text}
            </p>
          ))}
        </div>
      </div>
    </section>
  )
}
