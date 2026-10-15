# Status and integration log

Updated every evening at 21:00 after deploying `dev` and running the golden paths that exist. Agents read this to
know what already works; humans append one block per day.

## Current state
- Live model: `gemini-3.8-live` in `us-central1` (T05, Oct 13)
- Works on dev: `/api/healthz` on `ustaad-api-dev` (https://ustaad-api-dev-945574998233.asia-south1.run.app)
- Works on demo: PWA shell at https://ustaad101.web.app shows the server status; `/api/healthz` answers through
  the Hosting rewrite to `ustaad-api` (min instances 0, deployed from the local tag `v0-skeleton`)
- Works locally (not deployed): `/ws/live` stub answers pings; `MOCK_LIVE=1 make dev-api` replays the G2 script
  from `seed/fixtures/live_session.jsonl` (T09, Oct 13). Its step texts are placeholders until T08's real notes.
- Works locally (not deployed, T11, Oct 14): `/ws/live` runs a real `gemini-3.8-live` session; the job screen
  `/w/job/<id>?lang=hi` holds a push-to-talk Hindi turn with spoken reply and captions, barge-in (`interrupted`), and
  reconnects with the resume handle after a dropped connection (headless Chromium, recorded clip as the mic). Reply
  starts 0.9–1.1 s after release.
- Works on dev (T11, Oct 14, A's Android phone over a temporary preview link, since closed): Hindi question answered
  aloud with captions; pressing the mic stops Ustaad at once; Wi-Fi off shows the Hindi "reconnecting" notice and the
  session resumes with its handle. After Wi-Fi came back the phone reconnected 4 times in about 3 minutes (dev logs),
  each 2 s after the previous socket ended, so the next turn was slow to start. The server is not the cause: a
  resumed session stayed open 90 s idle and still knew the worker's name and brand. Likely the phone switching
  networks; recheck on 4G only.
- Not yet measured on 4G. Ustaad's captions often come back in Latin
  letters (instruction wording, see the T11 PR). The laptop clip's input transcript is wrong ("AC chal raha hai,
  laptop…") even when sent straight to the model, so judge transcription quality on the phone.
- Works locally against real models (T17, Oct 15; headless Chromium with a fake back camera, local `/ws/live`,
  uploads signed by the dev API; no phone yet): `request_media` opens the camera sheet with a live viewfinder in
  0.3 s; the phone-side check catches a very blurry photo in ~0.22 s with no upload; a blurry photo sent anyway
  gets the Hindi retake reason on the same request, and Ustaad says it 0.7–0.8 s later; the sharp retake is accepted
  and Ustaad speaks the findings 1.6–1.9 s after the result. A dropped socket resumed with its handle gets the open
  request again and the answer reaches the resumed session (2/2). A gate photo is judged by the gate check alone.
  Measured: one Flash photo check takes ~5 s, with outliers of 15–25 s (T27: timeout or "still checking").
  Who opens a photo request (Oct 15, real model): Ustaad opened the gate photo request himself for 1 of 5 gates
  and for 1 of 3 side-issue offers (otherwise he only said "bhejo"), 2 of 2 for a manual page. So the server now
  opens a gate's request itself, 4 ms after `safety_gate`; a wrong photo fails the gate with a Hindi reason and
  Ustaad says why from the server's note. A failed or hung vision call (30 s) asks for the photo again.
  The worker can start a photo himself ("फ़ोटो भेजो" beside the mic, `media_offer`): the sheet opens 0.7–1.0 s
  after the tap with no model in the way, and with the new instruction lines Ustaad talked about his photo 3/3
  (1.5–1.75 s after the result) and opened a request for a spoken photo offer 3/3 (was 1/3). After a gate photo
  passed, Ustaad called `next_step` only 3/5 (2/5 he said the step from memory, no step card). So the server now
  hands out the next step itself after a pass, through the same gate-checked `next_step`: step card 5/5 within
  0.4 s, Ustaad spoke that step 5/5, and never also called `next_step` (no skipped step, 5/5, two-step plan).
  First phone test (Oct 15, A's Android, office AC, preview link on dev): the sheet locked on "checking" after two
  retakes with the same reason (fixed: every server answer unlocks it); no zoom in the in-page camera (added 1x/2x/4x
  where the camera supports it); the viewfinder was a wide strip of a tall photo (now portrait, so what he sees is
  sent); the sheet now fits above the mic at 360 x 800. Phone-side sharpness on two real photos: blurred 6.3, sharp
  683 (threshold 15).
  Found and fixed: `read_photo` (T16) closed its Gemini client mid-call, so no gate photo could pass on dev.
  The local API cannot sign upload URLs with a user login (it needs the runtime service account).
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
| Text turn en (added with the English-profile decision) | PASS, first audio 1.1 s | not run | not run |
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
