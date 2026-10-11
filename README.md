# Ustaad — the senior technician in every repair worker's pocket

Ustaad is a voice-first assistant for Indian AC and appliance repair technicians. It turns a technician group's
WhatsApp voice notes into searchable, cited fault cards, guides a worker step by step by voice in Hindi, Telugu,
Tamil or Bengali while he stands at the broken unit, asks for photos when it needs to see, stops him at safety
steps, checks his stock and gets quotes from nearby parts shops on WhatsApp.

Built for the Google Cloud AI Builder Cup 2026 — theme: Future of Work & Enterprise Productivity.

> Live demo: _(link after first deploy)_ · Video: _(link)_ · Deck: `docs/deck.pdf`

## For judges (2 minutes)
1. Open the live link on a phone, tap **Try the demo**.
2. Tap the job, hold the mic, and ask "E6 aa raha hai, kya karun?" (or tap a sample photo).
3. Open `/d/import` on a laptop to watch a WhatsApp export become fault cards.
Seeded and synthetic data is labelled in the app.

## Built with
Gemini Live and Gemini Flash on Google Cloud Agent Platform, Agent Development Kit, Memory Bank, Agent Search,
Cloud Run, Firestore, Cloud Storage, Firebase Hosting, Places API, WhatsApp Cloud API.
Built with AI coding agents under one shared rule set (`AGENTS.md`); each PR records the tools used (see `docs/WORKFLOW.md`).

## For the team
Team: Kaustubh Upadhyay ([@KaustubhUp025](https://github.com/KaustubhUp025), voice and agent) and Samyak Jain
([@samyak8796](https://github.com/samyak8796), knowledge and commerce).
Start with `docs/SETUP.md`, then `docs/WORKFLOW.md`. Ground truth: `docs/SPEC.md`. UI: `docs/DESIGN.md`.
Rules for any AI coding agent: `AGENTS.md`; playbooks in `docs/playbooks/`; commands via `make`.

## Limits
Prototype: demo authentication only; WhatsApp vendor flow uses Meta's test number (5 registered phones);
error-code guidance comes from imported notes and manuals and is not a substitute for brand service training.

Licence: Apache-2.0
