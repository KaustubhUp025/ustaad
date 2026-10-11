# Playbook: build or polish a screen

Works with any coding agent. Start it with: "Follow docs/playbooks/ui-pass.md for <screen/route>".
This is the project's version of a distinctive-design process (plan, check against generic defaults, build,
critique with screenshots). If your tool has its own design skill or plugin, you may use it too, but
`docs/DESIGN.md` always wins where they differ.

## Steps
1. Read `docs/DESIGN.md` and `web/AGENTS.md`. Note which tokens, type roles and layout the screen uses.
2. Plan in 5–8 lines: the screen's single job, what the worker sees first, the one primary action, the states
   (empty, loading, error, offline, safety stop where relevant), and the exact copy in the default language.
3. Check the plan against DESIGN.md's "review against generic defaults" table. If any part reads like a template
   (identical rounded cards, eyebrow labels, scattered fade-ins, raw hex colours), change it and say what changed.
4. Build with tokens from `tokens.css` and strings from `src/i18n/`. No new colours, fonts or shadows.
5. Screenshot at 360 px and 1280 px wide: `pnpm -C web exec playwright screenshot --viewport-size=360,800 http://localhost:5173/w/job/demo shots/job-360.png`
   (Playwright is a web dev dependency) or your tool's own browser. Compare with DESIGN.md: hierarchy, one primary action, contrast in light and dark, Indian scripts render.
6. Fix what's off, screenshot again, then `make check`. Attach the final screenshots to the PR.

## Quality floor
360 px works · 48 px targets · visible focus · `prefers-reduced-motion` respected · Hindi and Telugu render
without fallback boxes · errors say what happened and what to do · seeded data labelled.
