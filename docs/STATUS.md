# Status and integration log

Updated every evening at 21:00 after deploying `dev` and running the golden paths that exist. Agents read this to
know what already works; humans append one block per day.

## Current state
- Live model: _pending T05_
- Works on dev: nothing yet (starter repo)
- Blocked: T03 budgets — billing-account permission is required to verify currency and existing budgets before creating alerts.

## Infrastructure status (2026-10-12)

Reported cloud results (not independently rechecked in this documentation update): required APIs enabled;
Firestore `(default)` and `demo` in `asia-south1`; `gs://ustaad101-media`; runtime service account and required
IAM bindings; placeholder Secret Manager versions; all four fault-card vector indexes READY; Firebase enabled
with its default Hosting site. No application deployment has occurred.

Remaining checks: create or verify the INR 500/2,000/5,000 budgets after billing-account access is granted, and
verify both teammates' cloud access. WhatsApp and Places integrations remain unusable until their placeholder
secret versions are replaced with working credentials. `web/package.json` is currently absent, so frontend
typecheck and build checks remain skipped until T04 scaffolds the web app.

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
