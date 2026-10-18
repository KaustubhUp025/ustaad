<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/svg/ustaad-lockup-dark.svg">
    <img alt="Ustaad" src="docs/brand/svg/ustaad-lockup-light.svg" height="96">
  </picture>
</p>

# Ustaad — the senior technician in every repair worker's pocket

Ustaad is a voice-first assistant for Indian AC and appliance repair technicians. It turns a technician group's
WhatsApp voice notes into searchable, cited fault cards, guides a worker step by step by voice in Hindi, Telugu,
Tamil or Bengali while he stands at the broken unit, asks for photos when it needs to see, stops him at safety
steps, checks his stock and gets quotes from his parts shops (on Telegram for the demo; WhatsApp is the future production
path because Meta business accounts were locked).

Built for the Google Cloud AI Builder Cup 2026 — theme: Future of Work & Enterprise Productivity.

> Live demo: _(pending)_ · Video: _(pending)_ · Final screenshots: _(pending)_ · Deck: `docs/ustaad-deck-skeleton.pdf`

## Recorded checks
These are recorded results, not targets: Agent Search returns page-cited results from Voltas, Daikin and LG manuals in
2.4–3.2 seconds. The import run produced 11 fault cards from 20 voice notes; the 20-card target was not met. Onboarding
checks passed 9/9 in Hindi and Telugu. Gate-photo checks recorded MCB at 5.4/6.0 seconds and PCB at 8.8/10.4 seconds.
Any unmeasured metric remains pending.

## For judges (2 minutes)
1. Open the live link on a phone, tap **Try the demo**.
2. Tap the job, hold the mic, and ask "E6 aa raha hai, kya karun?" (or tap a sample photo).
3. Open `/d/import` on a laptop to watch a WhatsApp export become fault cards.
Seeded and synthetic data is labelled in the app.

## Built with
Gemini Live and Gemini Flash on Google Cloud Agent Platform, Agent Development Kit, Memory Bank, Agent Search,
Cloud Run, Firestore, Cloud Storage, Firebase Hosting, Places API, Telegram Bot API (demo fallback; WhatsApp Cloud API after Meta verification).
Built with AI coding agents under one shared rule set (`AGENTS.md`); each PR records the tools used (see `docs/WORKFLOW.md`).

## For the team
Team: Kaustubh Upadhyay ([@KaustubhUp025](https://github.com/KaustubhUp025), voice and agent) and Samyak Jain
([@samyak8796](https://github.com/samyak8796), knowledge and commerce).
Start with `docs/SETUP.md`, then `docs/WORKFLOW.md`. Ground truth: `docs/SPEC.md`. UI: `docs/DESIGN.md`.
Rules for any AI coding agent: `AGENTS.md`; playbooks in `docs/playbooks/`; commands via `make`.

### Vendor quotes bot (Telegram)
Quote requests (M8) go to vendors through a Telegram bot for the demo. Meta locked both WhatsApp business accounts;
WhatsApp Cloud API is the future production path.
1. Create the bot with @BotFather (`/newbot`) and store its token without pasting it anywhere:
   `read -rs T && printf '%s' "$T" | gcloud secrets versions add tg-bot-token --data-file=-`
   (`infra/setup.sh` creates `tg-bot-token` and a random `tg-webhook-secret`).
2. Each vendor phone opens the bot and presses **Start** (a bot can only message chats that started it).
3. List their chat IDs and save them as the demo worker's vendors on dev:
   `TG_BOT_TOKEN=$(gcloud secrets versions access latest --secret tg-bot-token) uv run --directory backend --env-file .env python ../infra/tg_chat_ids.py --seed`
4. Deploy (`make deploy-dev`), then point the bot at the service: `PROJECT_ID=… ./infra/tg_set_webhook.sh`
   (`ENV=demo` for the judged service). Run step 3 before this: getUpdates stops once a webhook is set.

## Limits
Prototype: demo authentication only; vendor quotes go to team phones through a Telegram bot (see below);
error-code guidance comes from imported notes and manuals and is not a substitute for brand service training.

Licence: Apache-2.0
