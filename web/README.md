# web — Ustaad PWA (worker app /w + dashboard /d)

Scaffold on Day 1 (A, task T04), keeping `src/styles/tokens.css`:

```bash
pnpm create vite@latest . --template react-ts   # run inside web/, keep existing files
pnpm add react-router-dom react-i18next i18next @tanstack/react-query leaflet react-leaflet framer-motion
pnpm add -D tailwindcss @tailwindcss/vite vite-plugin-pwa openapi-typescript @playwright/test
pnpm dlx shadcn@latest init
```

Then:
- Import `src/styles/tokens.css` in `main.tsx`; map Tailwind theme colours to the CSS variables (no raw hex in components).
- Add `"typecheck": "tsc --noEmit"` to package.json scripts (CI runs it).
- Download DSEG7 Classic (SIL OFL 1.1) woff2 into `public/fonts/` for the error-code readout.
- `vite-plugin-pwa` manifest: name "Ustaad", `share_target` per docs/SPEC.md §8.
- Design rules: `docs/DESIGN.md`; process: `docs/playbooks/ui-pass.md`. Local agent rules: `web/AGENTS.md`.
