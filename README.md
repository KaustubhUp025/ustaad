# Ustaad — the senior technician in every repair worker's pocket

Ustaad is a voice-first assistant for Indian AC and appliance repair technicians. It turns a technician group's
WhatsApp voice notes into searchable, cited fault cards, guides a worker step by step by voice in Hindi, Telugu,
Tamil or Bengali while he stands at the broken unit, asks for photos when it needs to see, stops him at safety
steps, checks his stock and gets quotes from his parts shops on Telegram.

Built for the Google Cloud AI Builder Cup 2026 — theme: Future of Work & Enterprise Productivity.

> Live demo: _(link after first deploy)_ · Video: _(link)_ · Deck: `docs/deck.pdf`

## For judges (2 minutes)
1. Open the live link on a phone, tap **Try the demo**.
2. Tap the job, hold the mic, and ask "E6 aa raha hai, kya karun?" (or tap a sample photo).
3. Open `/d/import` on a laptop to watch a WhatsApp export become fault cards.
Seeded and synthetic data is labelled in the app.

## Built with
Gemini Live and Gemini Flash on Google Cloud Agent Platform, Agent Development Kit, Memory Bank, Agent Search,
Cloud Run, Firestore, Cloud Storage, Firebase Hosting, Places API, Telegram Bot API.
Built with AI coding agents under one shared rule set (`AGENTS.md`); each PR records the tools used (see `docs/WORKFLOW.md`).

## For the team
Team: Kaustubh Upadhyay ([@KaustubhUp025](https://github.com/KaustubhUp025), voice and agent) and Samyak Jain
([@samyak8796](https://github.com/samyak8796), knowledge and commerce).
Start with `docs/SETUP.md`, then `docs/WORKFLOW.md`. Ground truth: `docs/SPEC.md`. UI: `docs/DESIGN.md`.
Rules for any AI coding agent: `AGENTS.md`; playbooks in `docs/playbooks/`; commands via `make`.

### Vendor quotes bot (Telegram)
Quote requests (M8) go to vendors through a Telegram bot. WhatsApp Cloud API is the production path: our test number
was blocked by Meta business verification (error 131031), so the demo uses Telegram until a business is verified.
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
