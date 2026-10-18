import { useTranslation } from 'react-i18next'

/**
 * Ustaad logo (service tag + उ). Files live in web/public/brand/.
 *
 * - `mark`           full mark with the copper cord, 48 px and up
 * - `mark-simple`    no cord, for 20–47 px (header icons, chips)
 * - `lockup`         mark + "Ustaad" + "उस्ताद", horizontal (app header, dashboard rail)
 * - `lockup-stacked` mark above the words (splash, empty states, video end card)
 *
 * `on` is the background the logo sits on, which picks the text colour of lockups.
 */
type Variant = 'mark' | 'mark-simple' | 'lockup' | 'lockup-stacked'
type Surface = 'light' | 'dark'

interface UstaadLogoProps {
  variant?: Variant;
  on?: Surface;
  /** Rendered height in px; width follows the artwork's aspect ratio. */
  height?: number;
  className?: string;
  /** Set when a visible "Ustaad" label sits next to the logo, so screen readers don't hear it twice. */
  decorative?: boolean;
}

export function UstaadLogo({
  variant = 'lockup',
  on = 'light',
  height = 40,
  className,
  decorative = false,
}: UstaadLogoProps) {
  const { t } = useTranslation()
  const file = variant.startsWith('lockup') ? `ustaad-${variant}-${on}.svg` : `ustaad-${variant}.svg`
  return (
    <img
      src={`/brand/${file}`}
      alt={decorative ? '' : t('brand.name')}
      style={{ height, width: 'auto' }}
      className={className}
      draggable={false}
      decoding="async"
    />
  )
}
