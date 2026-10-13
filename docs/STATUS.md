# Status and integration log

Updated every evening at 21:00 after deploying `dev` and running the golden paths that exist. Agents read this to
know what already works; humans append one block per day.

## Current state
- Live model: `gemini-3.8-live` in `us-central1` (T05, Oct 13)
- Works on dev: `/api/healthz` on `ustaad-api-dev` (https://ustaad-api-dev-945574998233.asia-south1.run.app)
- Works on demo: PWA shell at https://ustaad101.web.app shows the server status; `/api/healthz` answers through
  the Hosting rewrite to `ustaad-api` (min instances 0, deployed from the local tag `v0-skeleton`)
- Memory Bank: empty Agent Engine `8060748716522340352` in `us-central1` (`AGENT_ENGINE_ID`)
- Blocked: —

## Infrastructure status (2026-10-12)

Reported cloud results (not independently rechecked in this documentation update): required APIs enabled;
Firestore `(default)` and `demo` in `asia-south1`; `gs://ustaad101-media`; runtime service account and required
IAM bindings; placeholder Secret Manager versions; all four fault-card vector indexes READY; Firebase enabled
with its default Hosting site. No application deployment has occurred.

Budgets: `ustaad-500`, `ustaad-2000` and `ustaad-5000` (INR, this project only, alerts at 90% and 100%) were created
on Oct 12 from the billing account owner's login (A); B has no billing-account access and does not need it. Both
teammates are project Owners. WhatsApp and Places integrations remain unusable until their placeholder
secret versions are replaced with working credentials. The web app was scaffolded and first deployed on Oct 13 (T04).

## Live smoke test (T05, 2026-10-13)

`make smoke-live` with `LIVE_MODEL=gemini-3.8-live`, run three times from a laptop in India:

| Check | `us-central1` | `global` | `asia-south1` |
| --- | --- | --- | --- |
| Text turn hi / te / ta / bn: audio, transcript in own script | PASS, first audio 1.0–1.4 s | model not found | model not found |
| One BLOCKING tool call, then spoken reply | PASS | model not found | model not found |
| Hindi clip in: input transcription and spoken reply | PASS | not run | not run |

The Hindi clip check passed first with a synthetic clip (made with `TTS_MODEL`), then with a real 6 s recording
from the laptop microphone ("AC chal nahi raha hai"); a phone recording in a noisy room is still untested. The real
clip timed out until 1.5 s of silence was appended: a turn only ends when the model hears silence after the last
word, which T11's push-to-talk release must provide. Its input transcript came back in Latin letters, not
Devanagari. First-audio times are for text turns over home broadband, not speech over 4G.

## Measured quality bar (fill on Thu, T29; the deck uses these numbers)
| Measure | Target | Actual |
| --- | --- | --- |
| Speech end → reply starts (p50, 4G) | ≤ 2.5 s | |
| Photo → findings spoken (p50) | ≤ 6 s | |
| Golden photos identified | 6/6 | |
| Import 30 notes | ≤ 2 min, ≥ 20 cards, ≥ 80% correct | |
| Quote round trip | ≤ 2 min | |
| Safety bypass tests | 0/10 succeed | |

## Log
| Date | Golden paths passing | What broke | Owner of fix |
| --- | --- | --- | --- |
| 2026-10-11 | — | — | — |
