# Status and integration log

Updated every evening at 21:00 after deploying `dev` and running the golden paths that exist. Agents read this to
know what already works; humans append one block per day.

## Current state
- Live model: _pending T05_
- Works on dev: `/api/healthz` on `ustaad-api-dev` (https://ustaad-api-dev-945574998233.asia-south1.run.app)
- Works on demo: PWA shell at https://ustaad101.web.app shows the server status; `/api/healthz` answers through
  the Hosting rewrite to `ustaad-api` (min instances 0, deployed from the local tag `v0-skeleton`)
- Memory Bank: empty Agent Engine `8060748716522340352` in `us-central1` (`AGENT_ENGINE_ID`)
- `LIVE_MODEL=gemini-3.8-live` on both services is a placeholder until T05 confirms it
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
