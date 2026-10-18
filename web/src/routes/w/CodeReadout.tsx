import { useTranslation } from 'react-i18next'

import type { Identified } from '@/audio/useLive'

// DESIGN.md's signature: the appliance's code in LED Cyan 7-segment digits, exactly as the AC shows it, with the
// brand and model beside it. It blinks twice when Ustaad reads the photo, then holds. The key restarts the blink for
// a new code.
export function CodeReadout({ identified }: { identified: Identified }) {
  const { t } = useTranslation()
  const { error_code: code, brand, model } = identified
  return (
    <section aria-label={t('live.seen')} className="flex items-center gap-4 border-t border-housing/15 bg-graphite px-4 py-3 text-housing">
      {code && (
        <span key={code} className="animate-readout font-code text-[length:var(--text-code)] leading-none text-led">
          {code}
        </span>
      )}
      <div className="min-w-0">
        <p className="truncate font-heading text-[length:var(--text-lg)] font-bold">{[brand, model].filter(Boolean).join(' · ')}</p>
        <p className="text-[length:var(--text-sm)] text-housing/75">{t('live.seen')}</p>
      </div>
    </section>
  )
}
