# Ustaad logo — service tag उ

The mark is a Meter Yellow service tag, tilted 6° as if just tied to a unit, with a copper cord through its
punched hole and the Devanagari letter **उ** (the first letter of उस्ताद). It reuses the step-card shape from
`docs/DESIGN.md`, so the logo and the app's service-tag cards read as one system.

All text in these files is converted to outlines, so nothing depends on fonts being installed.

## Files

### `web/public/` (served by Vite at the site root)
| File | Use |
| --- | --- |
| `favicon.ico` | 16 / 32 / 48 px; 16 px is hand-tuned (tag only, the letter can't survive that size) |
| `favicon.svg` | modern browsers' tab icon (graphite tile, no cord) |
| `apple-touch-icon.png` | 180 px, full-bleed graphite, iOS home screen |
| `pwa-64x64.png`, `pwa-192x192.png`, `pwa-512x512.png` | PWA install icons (rounded graphite tile, transparent corners) |
| `maskable-icon-512x512.png` | Android adaptive icon; the mark sits inside the 80% safe zone |
| `og-image.png` | 1200×630 link preview for the live demo URL |
| `brand/*.svg` | in-app logos, used by `UstaadLogo.tsx` |

### `docs/brand/`
| File | Use |
| --- | --- |
| `svg/ustaad-mark.svg` | master mark, full colour, with cord |
| `svg/ustaad-mark-simple.svg` | no cord, for 20–47 px |
| `svg/ustaad-mark-mono-graphite.svg` / `-mono-white.svg` | one-colour versions, letter knocked out (stamps, watermarks, the video overlay) |
| `svg/ustaad-icon*.svg` | sources for the app icons (tile, small tile, 16 px, maskable) |
| `svg/ustaad-lockup-{light,dark}.svg` | horizontal lockup; `light` = for light backgrounds, `dark` = for dark ones |
| `svg/ustaad-lockup-stacked-{light,dark}.svg` | stacked lockup (splash, deck title slide, video end card) |
| `svg/ustaad-wordmark-{light,dark}.svg` | words only, for places where the mark already appears |
| `svg/social-preview-1280x640.svg`, `svg/og-image-1200x630.svg` | sources for the banners |
| `png/github-avatar-500.png` | GitHub org/repo avatar (safe for a circular crop) |
| `png/social-preview-1280x640.png` | GitHub repo social preview: Settings › General › Social preview |
| `png/*.png` | 1200 px-wide lockups and 256/512/1024 marks for the deck and video |
| `source/` | the script that generated everything (see "Regenerating") |

## Rules
- **Sizes:** full mark at 48 px and up · `mark-simple` from 20 to 47 px · below 20 px use the favicon art.
- **Clear space:** keep at least the height of the punched hole ×2 (about 10% of the mark's width) free on every side.
- **Backgrounds:** Housing White `#EEF1EF`, Graphite `#1D2327` / `#182024`, or a photo with a solid tile behind the mark.
  Never place the yellow tag on Meter Yellow, or on any busy photo without a tile.
- **Don't:** recolour the tag, straighten or re-tilt it, swap उ for a Latin "U", add shadows, outlines or gradients,
  or put white text on the yellow (same rule as DESIGN.md).
- **Colours used:** Meter Yellow `#F6BE00`, Graphite `#1D2327`, Copper `#A9592D`; lockup text Graphite / `#4A555B`
  on light, `#EEF1EF` / `#A9B4B9` on dark.
- **Type in the lockup:** Archivo ExtraBold at 88% width ("Ustaad"), Noto Sans Devanagari Medium ("उस्ताद").

## Wiring it in

**`web/index.html`** — inside `<head>`:
```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1D2327">
<meta property="og:title" content="Ustaad">
<meta property="og:description" content="The senior technician in every repair worker's pocket.">
<meta property="og:image" content="https://YOUR-LIVE-DOMAIN/og-image.png">
<meta name="twitter:card" content="summary_large_image">
```
(`og:image` must be an absolute URL; replace the domain with the Firebase Hosting URL.)

**`web/vite.config.ts`** — the `VitePWA({...})` options:
```ts
includeAssets: ["favicon.ico", "favicon.svg", "apple-touch-icon.png"],
manifest: {
  name: "Ustaad",
  short_name: "Ustaad",
  theme_color: "#1D2327",
  background_color: "#EEF1EF",
  icons: [
    { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
    { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
    { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
    { src: "maskable-icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
  ],
},
```

**i18n** — add to `web/src/i18n/en.json` and `hi.json` (used for the logo's alt text):
```json
"brand": { "name": "Ustaad" }
```
```json
"brand": { "name": "उस्ताद" }
```

**In components:**
```tsx
import { UstaadLogo } from "@/components/brand/UstaadLogo";

<UstaadLogo variant="lockup" on="light" height={32} />          // worker app header
<UstaadLogo variant="lockup" on="dark" height={36} />           // dashboard left rail (dark mode)
<UstaadLogo variant="lockup-stacked" on="light" height={160} /> // splash / onboarding
<UstaadLogo variant="mark-simple" height={24} decorative />     // next to a visible "Ustaad" label
```

**README header** — switches with GitHub's light/dark theme:
```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/svg/ustaad-lockup-dark.svg">
    <img alt="Ustaad" src="docs/brand/svg/ustaad-lockup-light.svg" height="96">
  </picture>
</p>
```

## Regenerating
`source/build.py` rebuilds every file from the geometry and the brand fonts (Noto Sans Devanagari 500/800,
Archivo variable, Noto Sans). It needs `pip install fonttools brotli uharfbuzz cairosvg pillow` and the
font paths at the top of `source/glyphs.py` pointed at local copies of the fonts (`npm pack @fontsource/...`).
