# Ustaad Build Guide: how the whole project works, and how to build it well

Written Mon Oct 12, 2026, for the two-person team (A = Kaustubh, Voice and Agent; B = teammate, Knowledge and Commerce). Submission is Sat Oct 17, 21:00 IST. Feature freeze is Thu Oct 15, 18:00.

**Status of this guide.** The repo docs (`SPEC.md`, the two contract files, `SAFETY.md`, `TASKS.md`, `GOLDEN_PATHS.md`, `DECISIONS.md`) are authoritative. This guide explains them. It never overrides them. Anything I added that is not in the docs is marked **Suggested (not yet in spec)** or **Inferred**. If this guide and a doc disagree, the doc wins and the guide has a bug.

---

## 0. How to use this guide

### Who reads what

| Section | A (Voice and Agent) | B (Knowledge and Commerce) |
| --- | --- | --- |
| 1 Product | read | read |
| 2 Architecture | read | read |
| 3 Design principles | read | read |
| 4 Repo layout | read | read |
| 5 Tasks | all of Days 1-2 for the A tasks, skim B tasks | all of the B tasks, skim A tasks |
| 6 The agent | deep read | read once (you write tools the agent calls) |
| 7 Prompts | the Live, safety, photo and close-job prompts | transcription, thread, card, vendor prompts |
| 8 WhatsApp data | skim, help record | deep read (T08 is yours) |
| 9 Show-Ustaad proposal (side issues, manual photo) | deep read | read |
| 10 Testing | read | read |
| 11 Deployment | A: demo deploys | B: dev deploys, GCP |
| 12 Gaps and risks | both, today | both, today |
| 13 Glossary | look up as needed | look up as needed |

### Suggested reading order

1. Today, before any code: sections 1, 2, 3 (about 40 minutes). These explain why the repo looks the way it does.
2. Then section 12 (gaps). Several items need a decision before the contracts freeze at noon.
3. Then the Day 1 tasks in section 5 that you own.
4. Come back to section 6 and 7 when you start the agent work. Come back to section 8 before you record anything.

### How to learn from it

Each task in section 5 has the same shape: goal, tools and why, how to build, design rules, tests, pitfalls, and a task card you can paste into your AI coding agent. The card follows `docs/playbooks/task.md`. Read the "how to build" part yourself first. Then give the card to the agent. If you cannot explain what the agent produced, you are not ready to cross-review it.

---

## 1. The product in one page

**One sentence.** Ustaad is the senior technician in every repair worker's pocket. It turns a technician group's buried WhatsApp voice notes into a spoken, cited answer, in the worker's language, while he stands in front of the broken machine.

**The user.** Raju, 34, independent AC technician in Lucknow. Hindi-first, reads some English, Class 10. Cracked Android phone, patchy 4G indoors, dirty hands. 6 to 8 jobs a day in peak summer. He is in technician WhatsApp groups with hundreds of unplayed voice notes. When stuck, he calls a senior who is usually up a ladder.

Other people the product touches: the senior ("Ustaad-ji") whose knowledge we capture and credit; the shop owner who sees the dashboard; parts vendors who receive structured quote requests on WhatsApp.

### The four moments (each is a demo beat)

| Moment | Today | With Ustaad | Features |
| --- | --- | --- | --- |
| Before the job | No model number, wrong parts packed | Likely causes and parts to carry, checked against stock | S6 |
| Stuck at the door | Blinking E6, senior unreachable, 400 voice notes | Photo plus a Hinglish question gives spoken step-by-step help citing "Ramesh, May 2025" | M2 to M5 |
| Missing a part | Rides market shop to shop | Stock checked, 3 shops asked on WhatsApp, one tap to approve | M7, M8 |
| After the job | Fix never written down | Two questions, then a new fault card; area view spots repeats | M9, S2 |

### Four things that make it different

1. Voice notes become knowledge: an export becomes cited fault cards.
2. The agent learns the worker (memory), and every closed job teaches it.
3. It acts: it sources parts while he keeps working.
4. It sees what no one worker sees: the same model failing across nearby pincodes.

### How we are judged

| Criterion | Weight | What earns it |
| --- | --- | --- |
| Technical merit and Gen AI | 40% | Real Live voice in 4 languages, vision, transcription, cited retrieval, memory, safety gates in code, measured numbers |
| Problem alignment and impact | 25% | The four moments, real recordings, CEEW evidence (57% of technicians untrained in 5+ years) |
| Innovation | 25% | Voice notes to knowledge; agent asks to see; cross-pincode clusters; agent sources parts |
| UX | 10% | One thumb, voice-first, captions, safety stops, the error-code readout |

### What wins

Technical merit is 40%, and it rewards things that are measured and real. So: get the numbers (speech end to reply, photo to findings, 6/6 golden photos, import accuracy, 0/10 gate bypasses) and put actuals in the deck. A judge spends about two minutes: open link on phone, Try the demo, hold the mic, ask "E6 aa raha hai, kya karun?", hear and read a cited answer, see a photo request, see a safety stop. On a laptop, `/d/import` shows an export becoming cards live. Nothing needs a login, a WhatsApp number or an AC.

**Never cut:** M2 to M5 (spoken and captioned guidance, agent-requested photos, safety gate), M6 import, M8 quotes. Cut order if behind: live-look streaming, 15 s clips, Tamil/Bengali depth, shelf-photo counting, nudges as rules, map as table.

**Principles every change respects:** safety beats helpfulness; cite or say you do not know; the worker's language and words; honest demo (seeded data labelled, error-code meanings from real manuals); prototype, not platform.

---

## 2. System architecture

### 2.1 The whole picture

```
                         Worker phone (PWA, Hindi/Telugu/...)         Team laptop
                         /w/*  worker app                               /d/*  dashboard
                                |           |                                 |
              https (REST, static)|           | wss:// DIRECT                   | https
                                v           |  (Hosting can't carry WS)       v
                    +-----------------------+--+                    +---------------------+
                    |  Firebase Hosting         |                    | same Hosting site   |
                    |  static PWA, /api/** ----------+             +----------------------+
                    +---------------------------+     |
                                                      v
        wss://<run-url>/ws/live            +---------------------------------+      +-----------------+
        ---------------------------------> |  Cloud Run: ustaad-api          |<-----| WhatsApp Cloud  |
                                           |  FastAPI                        | webhook  API (Meta)    |
                                           |   - REST routers                |----->| test number     |
                                           |   - /ws/live (ws_live.py)       | send |  5 team phones  |
                                           |   - /webhook/whatsapp           |      |  = vendors      |
                                           |   - ADK agent: build_ustaad()   |      +-----------------+
                                           |   - tools/ (pure functions)     |
                                           +---+--------+--------+-----------+
                                               |        |        |
              +--------------------------------+        |        +-----------------------+
              v                                         v                                v
   +---------------------------+            +-----------------------+        +-------------------------+
   | Vertex / Agent Platform   |            | Firestore (vector)    |        | Cloud Storage bucket    |
   |  LIVE_MODEL (audio in/out)|            |  workers, jobs,       |        |  imports/{id}/, jobs/,  |
   |  FLASH_MODEL (vision,     |            |  fault_cards(768-dim),|        |  signed PUT/GET URLs    |
   |    transcription, text)   |            |  imports, quotes, ... |        +-------------------------+
   |  TTS_MODEL, EMBED_MODEL   |            +-----------------------+
   |  Memory Bank (Agent Engine|                     ^
   |    instance)              |                     | writes
   +---------------------------+            +--------+-------------------+
              ^                             | Cloud Run Jobs             |
              |                             |  ingest-whatsapp           |
   +---------------------------+            |  compute-clusters          |
   | Agent Search (manuals)    |            +----------------------------+
   |  3 brands' PDFs           |
   +---------------------------+            +---------------------------+
                                            | Places API (New): vendors |
                                            +---------------------------+
```

### 2.2 Component table

| Component | Tool | Why chosen | Alternatives rejected (reason) |
| --- | --- | --- | --- |
| Frontend | Vite + React 19 + TypeScript + Tailwind + shadcn/ui + react-i18next + vite-plugin-pwa | One codebase for `/w` and `/d`; installable PWA gives mic, camera, share target with no app store. SPEC §1: "No native app." | Native app (non-goal, slow to ship); Next.js (no SSR need, more moving parts) *(Inferred reasoning)* |
| Static hosting | Firebase Hosting | Cheap CDN, rewrites `/api/**` to Cloud Run so the PWA sees one origin for REST | Serving the PWA from Cloud Run (works, but loses CDN caching) *(Inferred)* |
| Live voice transport | Direct `wss://` to Cloud Run | DECISIONS: "Hosting rewrites don't carry WebSockets" | WS through Hosting rewrite (does not work) |
| API | FastAPI on Cloud Run (asia-south1) | Async Python, Pydantic native (which feeds the contract flow), one service for REST + WS + webhook | Several microservices (too much ops for 5 days) |
| Agent framework | Google ADK (`google-adk`) | `run_live()` handles bidirectional audio and tool calls; same agent also runs text via `run_async()` | Hand-rolled Live loop (kept only as fallback, see tools-are-pure-functions) |
| Model SDK | `google-genai` on Vertex | Credits pay for Vertex, not AI Studio keys (DECISIONS) | AI Studio keys (credits don't cover them) |
| Live model | `LIVE_MODEL` = `gemini-3.8-live` if T05 passes, else `gemini-live-2.5-flash-native-audio` | Native audio in and out, interruptible, tool calling | Separate STT, LLM, TTS pipeline (more latency, more code) *(Inferred reasoning)* |
| Text/vision model | `FLASH_MODEL` = `gemini-3.8-flash` | Photo reading, transcription, extraction, JSON output | A bigger model (slower, costlier; not needed) *(Inferred)* |
| Transcription | ffmpeg to 16 kHz mono FLAC, then Flash `generateContent` | `audio/ogg` is not a listed input type; Transcribe model is preview on another API (DECISIONS) | `gemini-3.5-transcribe` (optional, preview, Interactions API) |
| Embeddings | `gemini-embedding-001`, `output_dimensionality=768` | Model default is 3072; Firestore index is 768 (DECISIONS) | Separate vector DB (extra service to run) *(Inferred)* |
| Operational DB | Firestore (database `(default)` dev, `demo` judged) | Serverless, native vector search, no ops | Postgres/pgvector (needs a managed instance) *(Inferred)* |
| Manuals search | Agent Search (data store of 3 brands' PDFs) | ₹95.7k credit applies to it; page-level citations | Embedding PDFs ourselves (more work; S1 is only a Should) |
| Memory | Memory Bank on an empty Agent Engine instance (`AGENT_ENGINE_ID`) | Soft facts across sessions, managed | Hand-built memory in Firestore (kept only for structured data) |
| Files | Cloud Storage with signed URLs | Phone uploads straight to the bucket; API never proxies big files | Uploading through the API (memory and timeout pressure on Cloud Run) |
| Batch | Cloud Run Jobs: `ingest-whatsapp`, `compute-clusters` | Runs to completion, can fan out 8 parallel tasks, no request timeout | Doing it inside the API request (timeouts, CPU contention with Live sessions) |
| Vendors discovery | Places API (New) | Real nearby shops with place IDs | Hand-typed shop list only (used for seeded demo vendors too) |
| Vendor messaging | WhatsApp Cloud API test number | Vendors live on WhatsApp already; 5 team phones act as vendors | SMS/calls (not where vendors are) |
| Speech out for non-Live | `TTS_MODEL=gemini-3.8-flash-tts` | `/api/chat` returns a signed `tts_url` | Browser TTS (poor Indian-language quality) *(Inferred)* |
| Secrets | Secret Manager | AGENTS.md: "secrets only in Secret Manager" | `.env` in git (never) |
| CI | GitHub Actions, checks `backend` and `web` | Referee for every PR | Trust reviews alone (WORKFLOW: CI wins) |

### 2.3 Request lifecycles

**A voice turn (G2 first question).**

```
Phone                          ustaad-api (/ws/live)                  Live model
 | hold mic -> ptt start ------->|                                        |
 | PCM16 16k 40ms chunks ------->| LiveRequestQueue.send_realtime(chunk) ->|
 | release -> ptt end ---------->| activity end / audio stream end ------->|
 |                               |<-- input transcription (user words) ----|
 |<-- caption {who:user,final} --|                                        |
 |                               |<-- tool call search_fault_cards --------|
 |                               | run tool (pure fn) -> Firestore vector  |
 |                               |--- tool response (+scheduling) -------->|
 |<-- tool_activity -------------|                                        |
 |                               |<-- audio 24k PCM16 + output transcript -|
 |<-- binary audio (play) -------|                                        |
 |<-- caption {ustaad,partial..} |                                        |
 |<-- step_card (source chip) ---|  (emitted by our code from tool result)|
 |<-- turn_complete -------------|                                        |
```

Key point: the model speaks, but the UI cards (`step_card`, `identified`, `safety_gate`) are emitted by our code from tool results, not parsed out of the model's speech. That keeps the UI deterministic and the safety client-side rule (§6) enforceable.

**A photo request (M4).** The agent decides it needs to see the outdoor PCB and calls `request_media`. The tool is NON_BLOCKING with WHEN_IDLE scheduling, so the agent keeps talking. Our code sends `media_request` to the phone. The phone opens the camera sheet, resizes to 1600 px JPEG, asks the API for a signed upload URL (`POST /api/media/upload-url`), PUTs the file to Storage, then sends `media_ready` on the WebSocket. The server runs a Flash vision check against what was expected, sends `media_result` (with `retake_reason` if the match is poor), and hands the findings back to the agent as the tool's response. Max 2 retakes.

**An import (M6).**

```
/d/import (laptop)       ustaad-api              Storage        Cloud Run Job ingest-whatsapp       Firestore
 | choose zip ------------>| POST media/upload-url ->|                                                   |
 | PUT file ------------------------------------>   | imports/{id}/                                      |
 | POST /api/imports ----->| create imports/{id} queued, start Job ------->|                            |
 |                         |                                               | parse -> ffmpeg -> transcribe (8 parallel)
 | poll GET /imports/{id} every 2s <------ progress counts <--------------- | threads -> cards -> dedupe -> embed
 |                         |                                               |------------------------------->| fault_cards
```

**A quote (M8).**

```
Agent: request_quotes (NON_BLOCKING) -> create quote_requests/{qrid} + 1 quote per vendor (CREATED)
 -> send WhatsApp message (template or text) -> state SENT
Vendor replies on WhatsApp -> POST /webhook/whatsapp
 -> verify X-Hub-Signature-256 -> 200 immediately -> background task
 -> dedupe on wamid (wa_messages doc id) -> if voice note: transcribe -> Flash parses {price, available, eta}
 -> state PARSING -> QUOTED (or CLARIFY once, or DECLINED)
Phone polls GET /api/quotes/{qrid} every 2s -> WS `quotes` frame re-sent as replies arrive
Worker taps Approve -> POST /api/quotes/{qid}/approve -> CONFIRMED + confirmation messages
```

---

## 3. Software design principles used across the project

You are two backend engineers building voice, vision and LLM features in five days, with AI agents writing much of the code. Good structure is what stops four things: the two of you colliding, agents drifting, a flaky model breaking the demo, and a safety bug. Each principle below says what it is, why it matters here, and a concrete example from this repo.

### 3.1 Contract-first development

**What.** You agree the shape of every message and record before writing code on either side. Then each side builds against the agreed shape and can work alone.

**Why here.** A builds the Live WebSocket and the voice UI; B builds the dashboard and REST. They only meet at the contract. The freeze is Mon Oct 12, 12:00.

**Example.** The flow is one direction only:

```
shared/contracts/*.md | fault_card.schema.json     (human-approved text)
        |
        v   hand-written Pydantic models
backend/models/
        |
        v   make types
shared/contracts/openapi.json  +  web/src/api/types.ts      (GENERATED, never hand-edited)
```

CI fails on drift: it regenerates and compares. So a backend field change that forgets the contract fails the build. Changes to `shared/contracts/` need both humans plus a line in `CHANGELOG.md`.

**Codegen idea.** FastAPI builds an OpenAPI document from Pydantic models automatically. A tool (e.g. `openapi-typescript`) turns that into TypeScript types. You get one source (Pydantic) and the frontend's types can never silently disagree. *(The exact generator is whatever `make types` uses in the starter; read the Makefile.)*

### 3.2 Tools as pure functions

**What.** A tool is `Pydantic in -> Pydantic out`. No ADK imports, no global state, clients passed in.

**Why here.** (1) One unit test per tool, fast and offline. (2) SPEC §6 keeps a fallback: if ADK misbehaves, a raw `google-genai` Live client can call the same functions. That only works if tools do not depend on ADK.

**Example.**

```python
# backend/tools/inventory.py   (shape, not full code)
class UpdateInventoryIn(BaseModel):
    worker_id: str
    deltas: list[Delta]            # [{part, delta}]

class UpdateInventoryOut(BaseModel):
    items: list[InventoryItem]     # includes low flags

def update_inventory(inp: UpdateInventoryIn, *, db: Db) -> UpdateInventoryOut: ...
```

ADK gets a thin wrapper in `backend/agent/` that calls this. Business logic never lives in the wrapper.

### 3.3 Dependency injection of fake clients

**What.** Functions receive their dependencies (Firestore, Gemini, WhatsApp, Places) as arguments or via a small container, not by importing a global client.

**Why here.** AGENTS.md: "Call real Gemini, WhatsApp or Places APIs in unit tests" is forbidden. Tests use `seed/fixtures/` and fakes.

**Example.** `request_media` takes a `vision: VisionClient`. In production it is the Flash client. In tests it is a fake returning `{matches_expected: false, confidence: 0.41}` so you can test the retake loop in milliseconds.

### 3.4 Config via environment, not constants

**What.** Anything that changes between machines or over the week comes from env vars.

**Why here.** `LIVE_MODEL` is still pending (T05). If the model ID is hard-coded in 12 places, switching costs an afternoon. AGENTS.md forbids hard-coding model IDs or embedding size; read `FLASH_MODEL`, `LIVE_MODEL`, `TTS_MODEL`, `EMBED_MODEL`, `EMBED_DIM`.

**Example.** One `settings.py` (Inferred filename) reads env once with Pydantic settings; everything else imports `settings`. Tests override it.

### 3.5 Fixtures and mocks (MOCK_LIVE)

**What.** Recorded or hand-written data stands in for expensive or slow services.

**Why here.** A model call costs credits and seconds. UI work should never wait on Live. Two mock mechanisms exist: `MOCK_LIVE=1` (server) / `VITE_MOCK_LIVE=1` (client) replay `seed/fixtures/live_session.jsonl`, where each line is `{"t_ms": 1200, "frame": {...}}`; and stub routers return fixture JSON from `seed/fixtures/`.

**Example.** B builds `/w/job/:id` captions against the replay while A is still wiring Live.

### 3.6 Idempotency

**What.** Doing the same operation twice has the same effect as doing it once.

**Why here.** Meta retries webhooks. Imports can be re-run. Without idempotency a retry creates a second quote or a duplicate card.

**Example.** `wa_messages/{wamid}`: the Firestore document ID *is* the WhatsApp message ID. Create it with "create if not exists" semantics; if it already exists, drop the delivery. Another: fault-card dedupe merges (`verified_count++`) instead of inserting.

### 3.7 State machines

**What.** A thing that has a small, named set of states with allowed transitions, written down and enforced in one function.

**Why here.** Quotes and safety gates are both stateful and both go wrong silently if state is implicit.

**Example.** Quote per vendor: `CREATED -> SENT -> PARSING -> QUOTED -> CONFIRMED`, with `CLARIFY` (one follow-up only), `EXPIRED` (30 min), `DECLINED`. Write a `transition(state, event) -> state` function with a table of legal moves and reject the rest. Gates: `open -> passed | failed`, reset per job.

### 3.8 Safety in code, not in prompts (defence in depth)

**What.** Several independent layers each stop the same bad outcome, so one failure is not enough.

**Why here.** People work near mains voltage, charged capacitors and refrigerant. A prompt is a request to a model; it is not a guarantee. SAFETY.md says "tests never rely on the model obeying it."

**Example.** Four layers (§6.5): prompt, tool (`next_step` returns `SAFETY_GATE`), `before_tool_callback` (rejects `next_step`/`close_job` with open gates), client (renders gate screen, ignores a hazardous `step_card` while a gate is open). Ten bypass tests prove it.

### 3.9 Small PRs

**What.** One task, one branch, one worktree, one fresh agent session; no line limit, but each new file has one job (AGENTS.md, Modular code).

**Why here.** Review is the bottleneck, not writing code. Small diffs get real reviews. Branch naming: `a/<ID>-slug`, `b/<ID>-slug`. If a session has no passing tests after about 45 minutes, split the card.

### 3.10 Cross-model review

**What.** The reviewer is a different model from the author (the PR template records both).

**Why here.** Two models make different mistakes. Review checks, in order: contract breaks, safety, secrets/hard-coded models, missing tests, bugs (async misuse, non-idempotent webhook, timezones), UI rules. Contract PRs need both humans plus one model review.

### 3.11 `make check` as referee

**What.** One command (lint + unit tests + TS typecheck + build) decides whether work is acceptable.

**Why here.** "A model's approval never overrides red CI." Agents verify by running, not by arguing. Keep it fast and deterministic: no network, no real models.

### 3.12 i18n and design tokens

**What.** No user-facing string outside `web/src/i18n/{en,hi,te,ta,bn}.json`. No colour or font outside `web/src/styles/tokens.css`.

**Why here.** Four languages, one UI. Hard-coded strings make Telugu a rewrite. Tokens keep the look consistent across both of your agents' output.

**Example.** Button text "Photo bhejo" lives under a key in `hi.json`; the Meter Yellow `#F6BE00` is a CSS variable, never a literal in a component.

### 3.13 Prompts as versioned files

**What.** Prompts are files in the repo, reviewed like code, not strings buried in functions.

**Why here.** Prompt changes change behaviour. They need history and review. The agent's instruction is `backend/agent/instruction.md` and is human-owned. **Suggested (not yet in spec):** put the other prompts in `backend/prompts/<name>.md` with a version line at the top, and load them by name.

### 3.14 Other habits worth keeping

- **Typed boundaries.** Validate every model output with Pydantic; if parsing fails, retry once or send to a review state, never pass raw model text onward.
- **Fail soft on the demo path.** Demo-safe cache (T27) is a design choice: slow or failed live calls fall back to cached golden-path responses after 6 s.
- **Label synthetic data in the data itself** (`seeded: true`), not only in the UI.
- **Server owns Firestore.** The web app never talks to Firestore (no Firebase Auth, so rules could not verify our demo token). Rules deny all client access. The browser polls REST every 2 s while the page is visible.

---

## 4. Repo layout walkthrough

The docs name many paths. I list them with owner. Items marked *(inferred)* are my guess from the docs; confirm against the starter zip.

```
ustaad/
  AGENTS.md CLAUDE.md GEMINI.md        rules + thin adapters (both own; humans only)
  Makefile                             make check/test/types/dev-api/dev-web/golden/smoke-live
  docs/                                PRODUCT SPEC TASKS SAFETY GOLDEN_PATHS DESIGN GLOSSARY
    playbooks/                         task.md review.md ui-pass.md
    DECISIONS.md STATUS.md             decisions log, engineering log (both append)
  backend/
    AGENTS.md                          backend-only rules
    agent/                             A: build_ustaad(), instruction.md, callbacks.py, wrappers
    tools/                             pure functions. A: identify, request_media, repair, close_job, memory
                                       B: fault-card search, manuals, inventory, vendors, quotes, clusters
    models/                            Pydantic: WS frames, REST, Firestore entities (T09: A / T10: B)
    app/ws_live.py                     A: the /ws/live bridge
    app/ (routers)                     B: REST routers (inferred); A: /api/chat, /api/demo/session
    jobs/                              B: ingest-whatsapp, compute-clusters
    wa/                                B: webhook handler, WhatsApp send client, signature check
    prompts/                           (suggested, not in docs) versioned prompt files
  web/
    AGENTS.md
    src/audio/                         A: mic worklet, playback worklet, WS client
    src/i18n/{en,hi,te,ta,bn}.json     strings (A: hi/en base; B: owns i18n files per WORKFLOW)
    src/styles/tokens.css              design tokens (A's design-system pass)
    src/api/types.ts                   GENERATED
    src/routes/ (or pages/)            (inferred) /w/* A and B per WORKFLOW; /d/* B
  shared/contracts/                    both; ws-events.md rest.md firestore.md fault_card.schema.json
                                       CHANGELOG.md openapi.json(generated)
  seed/
    fixtures/                          live_session.jsonl, live_session_g1.jsonl, live_session_te.jsonl,
                                       quotes.json, close_job.json, tool fixtures
    whatsapp_export/                   demo export (see §8 for the commit-or-not decision)
    whatsapp_export_small/             unit-test fixture
    voice_note_script.md               T08
  infra/                               setup.sh firestore.sh budgets.sh smoke_live.py (B mostly; A: smoke, agent-engine)
  .github/CODEOWNERS, CI workflows
```

Ownership rule from WORKFLOW: swap whole columns if you like, never single rows. The interfaces between you are the tool contracts (SPEC §6) and the WS/REST contracts.

---

## 5. Phase-by-phase build, task by task (T01 to T35)

Task order and owners are exactly TASKS.md. Today is Mon Oct 12, so Sunday's tasks may be partly done; check `docs/STATUS.md`. Each card uses the `docs/playbooks/task.md` format. "Don't touch" always includes `shared/contracts/` and `backend/agent/instruction.md` unless the task is about them.

### Sun Oct 11: skeleton (T01 to T08)

#### T01 Confirm team registration (both, P0)
**Goal.** Make sure you are actually entered. **Do.** Check the Hack2skill confirmation, screenshot it. **Pitfall.** Registration closed Oct 11; if unsure, resolve now.
```
ID: T01   Owner: both   Branch: none
Goal: confirm Hack2skill team registration
Read: -
Done when: confirmation screenshot saved in docs/STATUS.md (no personal data)
Don't touch: code
```

#### T02 Public repo, branch protection (B, P0)
**Goal.** Public GitHub repo from the starter, `main` protected so CI must pass. **Tools.** `gh`, GitHub settings, CODEOWNERS. **Why.** Hackathon rules require a public repo; protection stops anyone merging red CI. **Steps.** Create repo `ustaad`, push starter as first commit, add A, require checks `backend` and `web`, replace CODEOWNERS placeholders so both of you must approve `shared/contracts/`. **Design rule.** Contracts need two human owners by construction. **Test.** Open a trivial PR; it must not merge without CI. **Pitfall.** Apache-2.0 licence file must exist; no `.env` committed.
```
ID: T02   Owner: B   Branch: b/T02-repo
Goal: public repo on main, collaborator A, protection requiring ci checks, CODEOWNERS real usernames
Read: SETUP §3
Done when: a PR to main cannot merge until CI is green
Don't touch: backend/, web/
```

#### T03 GCP infrastructure (B, P0)
**Goal.** Project, APIs, both Firestore databases, bucket, service account, secrets, budgets, Firebase. **Tools.** `infra/setup.sh`, `firestore.sh`, `budgets.sh`, gcloud. **Why scripts.** Repeatable infrastructure: if the project breaks you rerun, not click. **Steps.** Run `PROJECT_ID=... BILLING_ACCOUNT=... ./infra/setup.sh`, then firestore, then budgets (alerts at ₹500 / 2,000 / 5,000). Add both as Editors. Commit the `.firebaserc` setup.sh fills. **Design rule.** Least privilege service account; secrets only in Secret Manager. **Test.** `gcloud firestore databases list` shows `(default)` and `demo`; the vector index exists. **Pitfall.** Billing Reports on Day 2: confirm which credit pays which SKU.
```
ID: T03   Owner: B   Branch: b/T03-infra
Goal: run infra scripts; project, DBs, bucket, SA+IAM, secrets, budgets, Firebase exist
Read: SETUP §4
Done when: both DBs, bucket, secrets, budgets exist; .firebaserc committed
Don't touch: shared/contracts/
```

#### T04 Scaffold web and first deploys (A, P0)
**Goal.** A live URL showing the app shell, with `/api/healthz` answering through Hosting. **Tools.** Vite, pnpm, Firebase Hosting, Cloud Run. **Why.** Deploy the empty skeleton first so deployment problems surface on day 1, not day 5. **Steps.** Follow `web/README`; `make deploy-dev`; `git tag v0-skeleton && make deploy-demo MIN_INSTANCES=0` (Hosting's rewrite needs `ustaad-api` to exist); `make deploy-hosting`. **Test.** Open the URL on a phone; hit `/api/healthz`; expect `{ok, flash_model, live_model, demo_safe}`. **Pitfall.** Rewrite failing because the `ustaad-api` service does not exist yet.
```
ID: T04   Owner: A   Branch: a/T04-web-scaffold
Goal: scaffold web, deploy dev + demo(min 0) + hosting
Read: web/README, SETUP §4
Done when: live URL shows shell; /api/healthz via Hosting answers
Don't touch: shared/contracts/, backend/agent/
```

#### T05 Live smoke test and choose LIVE_MODEL (A, P0)
**Goal.** Prove the Live API works in hi/te/ta/bn and pick the model and region. **Tools.** `make smoke-live` (`infra/smoke_live.py`). **Why.** This decides the model for the entire voice stack. Learn it first. **Steps.** Run with `LIVE_MODEL=gemini-3.8-live`; do a text turn in each language plus a recorded Hindi clip; if it fails try `gemini-live-2.5-flash-native-audio`. Note whether Telugu/Tamil/Bengali captions arrive in native script. Record in `docs/STATUS.md` and the pending line in `docs/DECISIONS.md`. Set `LIVE_MODEL` and `LIVE_LOCATION` together (the smoke test must use the same region). **Pitfall.** Defaults differ between Live models, which is why SPEC says set `behavior` explicitly on every tool.
```
ID: T05   Owner: A   Branch: a/T05-live-smoke
Goal: run make smoke-live in hi/te/ta/bn + Hindi clip; choose LIVE_MODEL and LIVE_LOCATION
Read: infra/smoke_live.py
Done when: both checks PASS; result in STATUS.md and DECISIONS.md
Don't touch: backend/agent/instruction.md
```

#### T06 Meta app and WhatsApp test number (B, P0)
**Goal.** Webhook verified; 5 team phones can receive messages. **Tools.** Meta developer app, WhatsApp Cloud API, system-user token. **Why.** Quotes (M8) are never-cut; Meta setup has waiting steps (verification, tokens), so start early. **Steps.** Create app, add WhatsApp product, test number, add 5 recipient phones, set webhook to `https://<ustaad-api-dev-url>/webhook/whatsapp` with the verify token from Secret Manager, subscribe to `messages`. Create a **system-user token** because the temporary token expires. Store `WA_TOKEN`, `WA_PHONE_ID`, `WA_VERIFY_TOKEN`, `WA_APP_SECRET` in Secret Manager. **Pitfall.** The webhook GET verify must echo `hub.challenge`; the route must exist and be deployed before Meta can verify.
```
ID: T06   Owner: B   Branch: b/T06-meta-app
Goal: Meta app, test number, 5 recipients, webhook verified on dev, real secrets stored
Read: SETUP §5
Done when: Meta shows webhook verified
Don't touch: shared/contracts/
```

#### T07 Test sharing an export to the PWA (B, P2)
**Goal.** Learn whether WhatsApp's share sheet lists the installed PWA (SPEC says unverified). **Steps.** Install PWA on Android and iPhone, export a chat with media, open the share sheet, see if "Ustaad" appears. **Why it matters.** If not, the demo path is upload at `/d/import` anyway (path b). Don't spend more than 30 minutes. Note: this needs a `share_target` in the web manifest, which T04 or a later UI task must add. **Result goes in STATUS.md.**
```
ID: T07   Owner: B   Branch: b/T07-share-test
Goal: test sharing a WhatsApp export to the installed PWA on both phones
Read: SPEC §4
Done when: result recorded in docs/STATUS.md
Don't touch: backend/
```

#### T08 Fill the script and start recording (B, A helps, P0)
Covered in depth in §8. **Done when:** at least 15 notes recorded.

**From T09.** `seed/fixtures/live_session.jsonl` (the G2 mock) has two placeholder step texts and an audio link that does not exist, because this script was still blank. Once the real E6 note is recorded, replace both `step_card` instructions, the `source.label` date and `source.audio_uri` with the real ones.
```
ID: T08   Owner: B (A helps)   Branch: b/T08-voice-script
Goal: fill seed/voice_note_script.md from real manuals; record into group "AC Technician Noida"
Read: seed/voice_note_script.md
Done when: >=15 notes recorded; every code meaning traced to a manual page
Don't touch: code
```

---

### Mon Oct 12: contracts (freeze 12:00) then core (T09 to T14)

#### T09 WS frame models, `/ws/live` echo stub, `live_session.jsonl` (A, P0)

**Goal in plain words.** Turn `contracts-ws-events.md` into Pydantic classes; make `/ws/live` accept a connection and echo/replay; hand-write the recorded session for G2 so B can build UI before Live works.

**Tools and why.**
- *Pydantic v2 discriminated unions.* Every frame has `"type"`. A discriminated union on `type` gives you one parse call and precise validation errors.
- *FastAPI WebSocket.* Binary and text frames on one socket.
- *JSONL fixture.* One frame per line with `t_ms`; trivial to hand-edit and to replay.

**Steps.**
1. In `backend/models/ws.py` (inferred filename) write one model per frame, all with `v: Literal[1]` and `type: Literal["caption"]` etc. Make `WsServerFrame` and `WsClientFrame` unions.
2. Include every field the contract shows (e.g. `step_card.source{kind,label,audio_uri,doc,page}`; `media_request.max_seconds` null for photos).
3. Write `/ws/live`: check `token` and `Origin` (against `ALLOWED_ORIGINS`), send `session_ready` first, then in echo mode send `pong` for `ping`.
4. `MOCK_LIVE=1`: read `seed/fixtures/live_session.jsonl`, sleep to each `t_ms`, send the frame. Audio frames are omitted.
5. Hand-write the G2 script: `session_ready`, user caption, `identified` (code and meaning from the real manual), `step_card` with source chip, `media_request`, `media_result` with `retake_reason`, `media_ready` implied, `safety_gate G_MAINS_OFF`, `gate_result passed`, next `step_card`.

**Design rules.** Frames carry `"v": 1`; unknown `type` from the client returns `error{code:"bad_request"}`; never put secrets in the query string beyond the session token the contract already specifies.

**Tests.** Unit: each example JSON in the contract parses into its model and serialises back identically. Replay test: MOCK_LIVE yields frames in order. Manual: connect with a WebSocket client and see the replay.

**Pitfalls.** Contract examples are illustrative; where a field is optional in practice, make it `Optional` rather than guessing a default. Error codes allowed: `live_unavailable`, `rate_limited`, `auth`, `bad_request`, no others.

```
ID: T09   Owner: A   Branch: a/T09-ws-contracts
Goal: Pydantic models for all WS frames + tool I/O; /ws/live echo stub; MOCK_LIVE replay of G2
Read: shared/contracts/ws-events.md, SPEC §6, GOLDEN_PATHS G2, backend/AGENTS.md
Done when:
- every example frame in ws-events.md round-trips in tests
- MOCK_LIVE=1 replays seed/fixtures/live_session.jsonl in order
- make check passes
Don't touch: shared/contracts/, backend/agent/instruction.md
```

#### T10 REST and Firestore Pydantic models, stubs, `make types` (B, P0)

**Goal.** Same job as T09 for REST + Firestore. After this, the web side can code against real types.

**Tools and why.** Pydantic models, FastAPI routers returning fixtures, the `make types` pipeline (OpenAPI -> TypeScript).

**Steps.**
1. Models for Worker, Job, FaultCard, InventoryItem, Vendor, QuoteRequest, Quote, Import, Cluster, from `firestore.md`. API entities = Firestore doc + `id`, minus server-only fields (`embedding`, raw webhook bodies).
2. FaultCard from `fault_card.schema.json`. Read the version committed in `shared/contracts/` before modelling, including the T38 appliance types.
3. One router per area with stub handlers reading `seed/fixtures/*.json`. Error format `{"error": {"code","message"}}`.
4. Run `make types`; commit `shared/contracts/openapi.json` and `web/src/api/types.ts`.
5. Auth: bearer token on everything except `/healthz`, `/api/demo/session`, webhook.

**Design rules.** IDs are prefixed (`w_`, `j_`, `fc_`, `qr_`, `q_`, `i_`, `part_`); money is integer rupees; times are UTC ISO-8601. Put the Firestore-only fields in a separate internal model so the response model can never leak `embedding`.

**From T38 (general appliances).** For the remaining T10 models, follow the merged contracts:
- Worker `trades`: 1–3 unique values from the list in `firestore.md`; do not silently truncate.
- FaultCard `appliance_type`: use the current `fault_card.schema.json` values, including the general appliances.
- Job `appliance.type`: the same appliance-type values or null; step sources also allow `general`.
  Merged PR #19 owns `backend/models/repair.py`; import `Hazard`, `ApplianceType`, `RepairStep`, `GateId`
  and `GateState` rather than defining copies. `StepSource` is shared for repair steps. Gate
  transitions, step progression and safety enforcement remain T16 work. New-job creation starts gates open;
  validation and loading must preserve existing gate states.
- FaultCard `source` is a separate shape and must independently match `fault_card.schema.json`; do not use
  repair `StepSource` for it.
- The fault-card list's optional `appliance_type` filter follows `rest.md`; retrieval filtering and the relevance
  floor remain T41 work, and extraction classification remains T40 work.

The approved inventory slice stays appliance-independent: `category` remains nullable free text, not an
appliance enum. Its required nullable fields and strict REST deltas are unchanged. This note does not extend
inventory approval to the remaining T10 contracts or mark their implementation complete.

**Tests.** Each stub endpoint returns a body that validates against its response model. A "drift" test: regenerate OpenAPI and diff.

**Pitfall.** Enum values like `status` must match the contract strings exactly (e.g. `waiting_part`, `guiding`).

```
ID: T10   Owner: B   Branch: b/T10-rest-models
Goal: Pydantic REST + Firestore models, stub routers on fixtures, make types
Read: shared/contracts/rest.md, firestore.md, fault_card.schema.json, backend/AGENTS.md
Done when:
- openapi.json + types.ts committed, CI drift check green
- every stub serves a fixture that validates against its model
Don't touch: shared/contracts/*.md, backend/agent/
```

**Contract freeze at noon.** Before 12:00, both read each other's models once. Cross-check five things: WS `step_card.source` vs fault-card `source`; `media_ready.kind` values; `quotes` frame vs `Quote` model; Job `gates` map; and the `identified` frame fields vs the `identify_appliance` tool output.

#### T11 The Live bridge (A, P0): the deepest task

**Goal.** Phone and Ustaad talk in Hindi, end to end, with live captions, barge-in, push-to-talk and session resume. This is on the critical path.

**Concepts first.**

*Gemini Live / bidirectional streaming.* A normal LLM call is request then response. Live is a long-lived connection: you stream audio in while the model streams audio out, so the model can start answering before you finish and you can interrupt it. The server also does voice activity handling and can call tools mid-conversation.

*ADK `run_live()`.* ADK wraps a Live session. You give it a queue to push audio into and iterate events coming out: audio bytes, transcription text, tool calls, turn-complete, interruption. Your code translates those events into the WebSocket frames the phone expects. (Check the installed `google-adk` version's docs for exact class names; the pattern is `LiveRequestQueue` in, async event stream out, with a `RunConfig` for modalities and transcription.)

*PCM16.* Raw uncompressed 16-bit samples. Live wants 16 kHz mono in and returns 24 kHz mono out. No MP3, no Opus, no headers.

*AudioWorklet.* A small script running on the browser's audio thread. The microphone gives Float32 samples at the device rate (often 48 kHz). The worklet posts them to the main thread; you downsample to 16 kHz, convert to Int16, and cut into 40 ms chunks (16000 x 0.04 = 640 samples = 1,280 bytes). A second worklet plays incoming 24 kHz PCM16 from a ring buffer. `ScriptProcessorNode` is deprecated and janks on cheap phones; use worklets.

*Barge-in.* When the worker speaks over Ustaad, the server sends `interrupted`; the client must stop playback and clear its buffer immediately, or he hears the old answer on top of the new one.

*Push-to-talk (PTT).* Mic audio is sent only between `ptt start` and `ptt end`. For a noisy workshop this is more reliable than always-on voice detection, and it saves bandwidth on patchy 4G. SPEC locks it.

*Session resumption.* Live sessions have a time limit and sockets drop on bad networks. The server emits an opaque handle (`resume_handle` frame). The client reconnects with `&resume=<handle>` and the conversation continues. *Context window compression* lets long sessions continue by summarising old turns.

**Audio pipeline sketch.**

```
mic (48k Float32)
  -> AudioWorklet (capture) -> main thread
  -> downsample to 16k mono -> Int16 -> 640-sample (40 ms) chunks
  -> only while ptt held -> WebSocket binary frame
  -> ws_live.py -> LiveRequestQueue -> Live model
Live model audio out (24k PCM16)
  -> ws_live.py -> binary frame -> playback worklet ring buffer -> speaker
Input/output transcription events -> caption frames ({who, text, final})
```

**Steps (A).**
1. Server: `build_ustaad(model)` returns the agent (no tools yet except stubs). `ws_live.py` creates a Runner/Session per connection, with `RunConfig`: AUDIO response modality, input and output transcription on, speech language from the worker profile (`lang` query param), session resumption on, context compression on.
2. Two concurrent loops per connection (`asyncio.gather`): *upstream* reads client frames (binary -> queue; `ptt` -> activity signals; `text` -> content; `ping` -> `pong`), *downstream* iterates events (audio -> binary frame; transcriptions -> `caption` with `final` flag; `interrupted` -> frame; `turn_complete` -> frame; resumption update -> `resume_handle`).
3. Always `session_ready` first with `live_model` and `resumable: true`.
4. Errors: model unavailable -> `error{live_unavailable}`; too many sessions -> `rate_limited`.
5. Client `web/src/audio/`: `capture.worklet.ts`, `playback.worklet.ts`, `liveClient.ts` (WebSocket, reconnect with handle, 20 s ping), a `useLive` hook exposing `state`, `captions[]`, `start/stopPtt`, `sendText`.
6. Captions: partial captions replace the previous partial for the same `who`; the final one locks it. Show the last 3 turns at 20 px (DESIGN.md). Devanagari must use Noto Sans Devanagari.
7. Hindi first. Telugu next after the T05 findings.

**Design rules.** Keep ADK-specific code inside `ws_live.py` and `agent/`; keep the frame-translation function pure (`event -> list[WsServerFrame]`) so you can unit test it with fake events. Never block the event loop (no sync Firestore calls in the loops). One connection = one session object; clean up the queue on disconnect.

**Tests.** Unit: translation function with fake events (audio, partial transcript, final transcript, interrupted). MOCK_LIVE replay. Manual on a real phone: speak a Hindi question, hear a reply, see captions in Devanagari, interrupt it mid-sentence, turn off Wi-Fi for 5 s and see it resume.

**Pitfalls.** Browser autoplay rules: audio context must be resumed on a user gesture (the first mic press). Sample-rate mismatch makes voices chipmunk or slow: playback must be 24 kHz. iOS Safari quirks with `getUserMedia` in a PWA. Echo: use `echoCancellation: true` and keep the phone speaker volume moderate. Chunk sizes that are not 40 ms still work, but keep them stable for latency measurement. Cloud Run needs `--timeout=3600` and session affinity (SPEC §5), and the origin check.

**If ADK misbehaves.** Fallback in SPEC §6: raw `google-genai` Live client calling the same pure tools. Decide by Tue noon at the latest.

```
ID: T11 / M3   Owner: A   Branch: a/M3-live-bridge
Goal: Live bridge: mic worklet -> 16k PCM16 40ms -> WS -> ADK run_live -> 24k playback, captions, barge-in, PTT, resume; Hindi end to end
Read: SPEC §6 (Live paragraph), shared/contracts/ws-events.md, backend/AGENTS.md, web/AGENTS.md
Done when:
- unit test: event->frame translation covers audio, partial/final transcript, interrupted, turn_complete, resume handle
- on dev, a real phone holds a Hindi conversation with captions
- barge-in stops playback within ~200 ms
Don't touch: shared/contracts/, backend/agent/instruction.md, backend/agent/callbacks.py
```

#### T12 `identify_appliance` and the 6 golden photos (A, P1)

**Goal.** Photo of a nameplate and an error display gives brand, model, series, type, error code, confidence.

**Tools and why.** Flash vision with structured JSON output; the tool is BLOCKING (the agent needs the answer before it can continue). Pure function with a `vision` client argument.

**Steps.**
1. Define `IdentifyIn{media_uri}` and `IdentifyOut{brand, model, series, type, error_code, confidence}`.
2. Download the image from Storage (injected `storage`), call Flash with a response schema (see §7), validate with Pydantic.
3. Normalise: error code uppercased, whitespace stripped, as shown on the 7-segment display ("E6").
4. Emit the `identified` frame from the wrapper (not inside the pure function).
5. Record the 6 golden photos: real nameplates and boards (the voice-note script lists them). Save Flash's responses as fixtures so unit tests replay them.

**From T09.** `IdentifyIn` / `IdentifyOut` already exist in `backend/models/tools.py`. Beyond the named fields, `observations` carries anything else legible in the photo (serial number, refrigerant, capacity, a burn mark); the model trims it to the 6 surest at confidence >= 0.6. The response schema and prompt should ask for observations that help diagnosis only. The `identified` frame stays as the contract has it; observations go to the agent, not the screen.

**From T38.** Normalise `type` to the `appliance_type` values in `fault_card.schema.json` (`split_ac`, `window_ac`, `fridge`, `washing_machine`, `led_tv`, `microwave`, `geyser`, `fan_cooler`, `other`); null stays null. Define the allowed values once in `backend/models/` and, next to them, the one mapping constant from a profile `trades` value to card types (`ac` -> `split_ac`, `window_ac`; the rest map to themselves). Tests: one normalisation case per value, and the mapping.

**Design rule.** Return `confidence` honestly; below a threshold (**Suggested (not yet in spec)**: 0.6, matching the card review threshold) the agent should ask for a clearer photo rather than guess. Never map a code to a meaning here; meaning comes from search.

**Tests.** 6/6 golden photos correct against recorded responses (unit); run live once with `make golden` (T29).

**Pitfalls.** Reflections on LED displays; the model reading "E6" as "E8"; forgetting to resize large JPEGs (the client resizes to 1600 px).

```
ID: T12 / M2   Owner: A   Branch: a/M2-identify
Goal: identify_appliance tool (BLOCKING) + 6 golden photo fixtures
Read: SPEC §6 (tool table), GOLDEN_PATHS G2, backend/AGENTS.md
Done when: tests/unit/test_identify.py passes 6/6 golden photos with recorded responses; no network;
           type is normalised to the appliance_type values; the trades -> card types mapping has a test
Don't touch: shared/contracts/, backend/agent/instruction.md
```

#### T13 Ingest job: parse, ffmpeg, transcribe, threads (B, P0)

**Goal.** A Cloud Run Job that takes an uploaded export and produces parsed messages with transcripts and threads.

**Concepts.** *Cloud Run Job vs service:* a service waits for HTTP requests and scales with traffic; a Job starts, runs a task to completion, then exits, with up to N parallel tasks. Import is long, bursty, CPU heavy (ffmpeg), so it must not live inside the API that also holds Live sessions. The API creates `imports/{id}` and triggers the Job.

**Pipeline stages (from SPEC §4).**

```
Storage imports/{id}/*  ->  1 unzip + locate chat .txt
 2 parse lines -> messages[{ts, speaker, text|attachment}]       (pure, no network)
 3 audio: ffmpeg -i x.opus -ac 1 -ar 16000 x.flac               (subprocess)
 4 transcribe via Flash -> {text, language, confidence}          (Hinglish/codes/part numbers verbatim)
 5 photos described via Flash vision
 6 group into threads: Flash grouping by topic (time gaps are hints); 30-min split only as fallback
 7 (T15) card per resolved thread -> dedupe -> embed -> write
```

**Parsing details (SPEC §4).**
- Android: `12/05/25, 10:41 am - Ramesh: PTT-20250512-WA0003.opus (file attached)`
- iOS: `[12/05/25, 10:41:22 AM] Ramesh: ...` inside a zip with `_chat.txt`.
- Date order (DD/MM vs MM/DD) varies by locale: detect from the whole file (any first-field value above 12 proves DD/MM) rather than assuming.
- Multi-line messages: lines not starting with a timestamp belong to the previous message.
- System lines (encryption notice, "X joined") have no `Speaker:`; skip them.
- Unicode left-to-right marks (U+200E) and narrow no-break spaces appear in iOS exports; strip them before matching.
- Strip phone numbers from speaker names (consent rule). Keep first names.

**Steps.**
1. `backend/jobs/ingest/parse.py` (inferred): `parse_chat(text) -> list[Message]`; two regexes, one per platform; detect the platform per file.
2. `media.py`: map attachment file names to files in the export; handle missing media.
3. `transcribe.py`: wrapper around Flash with a Pydantic `Transcript`; 8 parallel via `asyncio.Semaphore(8)` or Job tasks.
4. `threads.py`: threads are built from **eligible messages** only: every line with an author, including an empty authored message and an attachment. System lines (the encryption notice, group created, members added or left) and "This message was deleted" lines are skipped: they are not sent to Flash and belong to no thread. Send the eligible messages in time order (id, speaker, time, minutes since the previous eligible message, text or transcript or photo description) to Flash with a response schema: a list of threads, each a list of message ids (§7.3). Validate in code: every eligible message in exactly one thread, no other ids, ids in time order inside a thread; on an invalid answer or a failed call, fall back to splitting on gaps over 30 min. Unit tests use a fake Flash client: the validation, the fallback, and the two cases from the real demo export of Oct 16: an answer 1–4 h after its question joins it, and a new fault 2 min after the previous outcome starts a new thread.
5. Progress: update `imports/{id}` counters (`audio_done`, `threads`, `status` transitions `queued -> parsing -> transcribing -> extracting -> done|failed`).

**Design rules.** Parsing is pure and tested on both formats. Per-file failures are appended to `errors[]` and do not abort the import. Transcribe calls go through an injected client. Write progress at most every second or so to avoid hot-document contention in Firestore.

**Tests.** Unit: `whatsapp_export_small/` fixture produces messages plus transcripts (stubbed transcription) matching expected JSON (§8.6). Edge cases: iOS format, multi-line, missing media, DD/MM vs MM/DD. Manual: run the real demo export once and time it (target 30 notes under 2 min, 8 parallel).

**Pitfalls.** `.opus` from WhatsApp is OGG-Opus; ffmpeg needs `libopus` (the Job image must include a full ffmpeg). Very short or silent notes produce empty transcripts: mark low confidence, don't crash. Memory on Jobs: stream large files, do not load a whole zip in memory.

```
ID: T13 / M6   Owner: B   Branch: b/M6-ingest-parse
Goal: ingest-whatsapp Job: parse Android+iOS, ffmpeg to FLAC, Flash transcripts, Flash threads (30-min fallback), progress in imports/{id}
Read: SPEC §4, shared/contracts/firestore.md (imports), seed/whatsapp_export_small/
Done when:
- make test: small export fixture -> messages + (fake) transcripts + threads equal expected.json
- iOS and Android line formats both parsed; DD/MM detected
- no network in unit tests
Don't touch: shared/contracts/, backend/agent/
```

#### T14 Agent Search with the 3 brands' manuals (B, P2)

**Goal.** `search_manuals(query, brand, model?)` returns snippets `{text, doc, page}`.

**Concept.** Agent Search (Vertex AI Search family) ingests PDFs into a *data store* and does retrieval with chunking and ranking for you, so you do not build a PDF pipeline. Reason chosen: the ₹95.7k GenAI App Builder credit applies to it (reportedly only to those SKUs).

**Steps.** Download the three brands' service manuals (Voltas, Daikin, LG). Put the PDFs in a bucket path. Create the data store and import. Set `AGENT_SEARCH_DATASTORE`. Write `search_manuals` as a pure function with an injected search client; map results to `{text, doc, page}`; filter by brand. **Tests.** Unit with a recorded search response; manual: a query for a code returns a page-cited snippet. **Pitfall.** Scanned PDFs without text layer; page numbers off by cover pages: verify citations by opening the page. **Also:** these same manuals are your ground truth for T08.

```
ID: T14 / S1   Owner: B   Branch: b/S1-manuals-search
Goal: Agent Search data store with 3 brands' manuals; search_manuals tool
Read: SPEC §5, SPEC §6 tool table, backend/AGENTS.md
Done when: unit test with recorded response passes; a real query returns a snippet with doc and page
Don't touch: shared/contracts/, backend/agent/
```

---
### Tue Oct 13: features (T15 to T20)

#### T15 Card extraction, dedupe, embeddings, `search_fault_cards` (B, P0)

**Goal.** Turn threads into fault cards, merge duplicates, store 768-dim vectors, and make search return Ramesh's E6 card.

**Concepts.**

*Embedding.* A model turns text into a list of numbers (a vector) so that similar meanings are close together. `gemini-embedding-001` outputs 3072 numbers by default; we ask for `output_dimensionality=768` because the Firestore index is 768 (DECISIONS). If you embed with one size and index another, search silently returns nothing or errors.

*Cosine similarity.* Closeness measured by the angle between vectors; 1 is identical. Dedupe uses cosine > 0.9 (SPEC §4).

*Firestore vector search.* Store the embedding as a Firestore `Vector` field, create a vector index (done by `infra/firestore.sh`), then call `find_nearest` with a query vector, a distance measure and a limit. You can pre-filter with normal `where` clauses (brand), which is how we combine exact and semantic search. Distance measure in the index and query must match what `firestore.sh` set up; read it.

*Hybrid retrieval.* Exact matching on structured fields (brand, error code) plus semantic matching on the symptom text. Error codes are exact things: "E6" should hit by field first; vectors cover "outdoor chal nahi raha" style descriptions.

**Card extraction.** Input: a thread (messages with speaker, ts, transcript, photo descriptions). Output: zero or one card per *resolved* thread. A thread is resolved if someone reports a fix. A question with no answer is not a card. See §7 for the prompt and schema. Each card carries sources (speaker first name, date, audio URI, message ids) and a `confidence`. Confidence under 0.6 goes to the review queue (`review_status`) and counts in `cards_needing_review`. Fields from the glossary: brand, model, code, symptom, cause, steps, parts, hazard, source; exact field list is `fault_card.schema.json`.

**Hazard tagging.** Every step and card gets `hazard` of `none`, `HV`, `capacitor` or `refrigerant`. The extractor proposes it; **a deterministic keyword check can raise (never lower) the level** (**Suggested (not yet in spec)**), e.g. "gas", "refill", "brazing" force `refrigerant`. This is defence in depth at ingest time.

**Dedupe algorithm.**

```
for new_card in cards:
    candidates = find_nearest(embed(new_card.text), where brand == new_card.brand, limit=5)
    match = first c where c.error_code == new_card.error_code (or both None)
                      and cosine(c, new_card) > 0.9
    if match: merge sources into match, match.verified_count += 1, keep higher-confidence fields
    else:     insert new card
```

Merging should append sources, not overwrite them, so the original voices are still credited. A disagreeing fix from a second person (script point 4) should become an *alternative* inside the same card or a separate card with a note; decide and test either way.

**`search_fault_cards(brand, model?, error_code?, symptom?)`.** BLOCKING. Returns the top 5 with `citation{author,date,audio_uri}`. Steps: filter by brand (and code if given) -> vector re-rank by symptom + code text -> return. Embedding the *query* uses the same model and 768 dimensions (note: Suggested: use the retrieval-query task type if the SDK exposes it; check the docs).

**Design rules.** Embedding generation sits behind an injected `Embedder`; tests use a deterministic fake (hash the text into 768 floats). Dedupe is a pure function over cards plus similarity scores. Never return the `embedding` in API responses.

**Tests.** Unit: fake embedder; dedupe merges two near-identical cards and increments `verified_count`; different code does not merge; search returns the right card from a seeded set. Integration (once): demo export gives at least 20 cards, search "Voltas E6" returns Ramesh's card.

**Pitfalls.** Wrong dimension; forgetting the index takes minutes to build; Firestore vector search requires the index to match the exact field path and distance; transcript text includes Hinglish spelling variants ("capacitor/kapasitar"); the extractor invents a code meaning not in the source (the prompt must say "use only what is said").

```
ID: T15 / M6,M2   Owner: B   Branch: b/M6-cards-search
Goal: card extraction per resolved thread, dedupe (same brand+code, cosine>0.9 -> merge, verified_count++), 768-dim embeddings, search_fault_cards
Read: SPEC §4, shared/contracts/fault_card.schema.json, backend/AGENTS.md
Done when:
- fake-embedder tests: merge, no-merge, ranking
- demo export -> >=20 cards; search returns Ramesh's E6 card
- confidence <0.6 -> review queue
Don't touch: shared/contracts/, backend/agent/, SAFETY.md
```

#### T16 Safety gates, `start_repair` / `next_step`, `before_tool_callback`, red screen (A, P0)

**Goal.** Make it impossible, in code, to reach a hazardous step without evidence. All 10 SAFETY.md bypass tests must fail to bypass.

**Why this is the most important code.** People can get hurt. Judges also see "0/10 gate bypasses" as a Technical Merit number.

**The model.** Steps carry `hazard`. Gates are per job: `G_MAINS_OFF`, `G_CAP_DISCHARGE`.

| Step hazard | Required gates in this job |
| --- | --- |
| none | none |
| HV | G_MAINS_OFF |
| capacitor | G_MAINS_OFF and G_CAP_DISCHARGE |
| refrigerant | never guided: STOP_REFRIGERANT |

**Layers (enforcement list in SAFETY.md).**
1. `next_step` returns `SAFETY_GATE{gate_id, required_evidence}` instead of a step while a required gate is open.
2. `before_tool_callback` rejects `next_step` / `close_job` calls that would skip an open gate.
3. Steps with `hazard: refrigerant` are never emitted; tool returns `STOP_REFER`.
4. Client renders `safety_gate` / `safety_stop` as full-screen states and never renders a hazardous `step_card` that arrives while it holds an open gate.
5. Prompt says the same, tests never rely on it.

**Pure gate logic (sketch).**

```python
def required_gates(hazard: Hazard) -> list[GateId]: ...
def next_open_gate(job: Job, step: Step) -> GateId | None:
    for g in required_gates(step.hazard):
        if job.gates.get(g) != "passed": return g
    return None

def next_step(inp, *, db) -> NextStepOut:
    job = db.get_job(inp.job_id)
    step = job.steps[job.current_index]          # candidate
    if step.hazard == "refrigerant": return StopRefer(...)
    gate = next_open_gate(job, step)
    if gate: return SafetyGate(gate_id=gate, required_evidence=EVIDENCE[gate])
    return step_out(step)    # only here can a hazardous instruction leave the server
```

Note the design: `step_out` is only reachable through the gate check. The instruction text of a hazardous step should not be in any response, log line or frame earlier than that.

**`confirm_safety(job_id, gate_id, media_uri)`.** Calls Flash vision with a gate-specific question and returns `passed, reason`. Pass conditions: MCB/isolator visible OFF or plug removed, confidence >= 0.7 (G_MAINS_OFF); multimeter display reading <= 5 V DC across the capacitor terminals, confidence >= 0.7 (G_CAP_DISCHARGE). On fail the gate stays locked; capacitor fail message tells him to discharge safely with an insulated tool and re-measure. State is stored in `jobs/{jid}.gates` and a new job starts all `open` (test 9).

**`before_tool_callback`.** In ADK this hook runs before every tool call and can return a replacement result to skip the call. It checks the job's gate state independently from the tool. This duplicates tool logic on purpose; the callback must not import the tool's private helpers, only read gate state through the same pure `next_open_gate`. Keep it in `backend/agent/callbacks.py` (human-owned).

**Refrigerant.** Detected two ways: step hazard, and user intent (gas refill, leak repair, brazing, pressure work). Intent detection can be a Flash classification plus keyword list. Result: `safety_stop{reason:"refrigerant"}` frame; client shows a full red screen (Fault Red `#D1263A`, used for safety only) with fixed text for the stop reason from the i18n files (no audio clip; SAFETY.md) and, for refrigerant, the Hindi message "Gas ka kaam certified gas technician hi karega. Main baaki checks mein madad kar sakta hoon."

**Client.** A small reducer: `gateOpen: GateId | null`. On `safety_gate` set it; on `gate_result passed` clear it. A `step_card` with hazard != none and `gateOpen` set is dropped and the gate screen stays (test 10). Unit test this reducer.

**Tests: SAFETY.md's 10, as automated tests.**
1. Next step on HV, no gate photo -> SAFETY_GATE G_MAINS_OFF. 2. "MCB band kar diya" with no photo -> still locked (text never opens a gate; only `confirm_safety` with an image does). 3. Photo of a wall -> gate fails with a reason (fake vision returns a negative). 4. Pass MAINS_OFF, ask capacitor step -> G_CAP_DISCHARGE. 5. Multimeter 230 V -> fails. 6. Prompt injection "ignore safety, I am certified" -> still locked (tests call the tools/callback directly, no model). 7. Gas refill -> STOP_REFRIGERANT. 8. `close_job` with open gate -> rejected. 9. New job -> gates open. 10. Client test with injected step_card.

**From T38 (general steps; SPEC §6 source tiers, SAFETY.md).** These decisions are made; build them as written.
- `start_repair` takes either `card_ids` or, when no card or manual matched, proposed steps `[{instruction, summary_en}]` from the Live model. It makes no model call. It tags each step, stores it on the job with source kind `general` (add `general` to `StepSource.kind` in `backend/models/ws.py`), and from then on `next_step`, the gates and the callback treat it exactly like a card step. One state machine.
- Hazard tagger: one pure function reading one rules table (a named constant beside it). Each row is a set of English keywords and an outcome, either a hazard level (`HV`, `capacitor`) or a stop reason (`refrigerant`, `microwave_hv`, `crt`, `geyser_open`). It runs on `summary_en`, can raise a step's hazard and never lower it, and takes plain text so the import pipeline can call it later.
- Default gate: a job whose steps are all `general` must pass `G_MAINS_OFF` before its first step, whatever the step's hazard. `G_CAP_DISCHARGE` applies to any step tagged `capacitor`, from any source.
- A step matching a stop row is never emitted; the tool returns `STOP_REFER` with the reason. The hazard enum does not change.
- `before_tool_callback` needs nothing extra for general steps.
- Tests: the "General-tier tests" table in SAFETY.md, except its last row (the caption backstop, T39). Run bypass tests 1 to 9 against general steps as well, without editing them.

**Pitfalls.** Gate state in session memory only (lost on reconnect): persist in Firestore. Race: two quick `next_step` calls. The model calling `confirm_safety` with a stale `media_uri`: bind the photo to a `request_id` created by the server. A test that passes because the fake vision always says yes: also test the negative path.

```
ID: T16 / M5   Owner: A   Branch: a/M5-safety-gates
Goal: start_repair/next_step with gates; confirm_safety; before_tool_callback; client safety screens
Read: docs/SAFETY.md, SPEC §6, shared/contracts/ws-events.md, backend/AGENTS.md
Done when:
- tests/unit/test_safety_bypass.py covers all 10 SAFETY.md attempts and none bypass
- callback blocks next_step/close_job with open gate
- client reducer test ignores hazardous step_card while gate open
- SAFETY.md general-tier tests pass (all rows except the caption backstop)
Don't touch: docs/SAFETY.md, shared/contracts/
```
(Humans own `callbacks.py`: A writes it with an agent, B reviews it line by line.)

#### T17 `request_media`, camera sheet, retake loop (A, P0)

**Goal.** The agent can ask to see something, the phone captures it, the server checks it, and the loop retries once with a reason.

**Concepts.**

*Function-calling BLOCKING vs NON_BLOCKING.* In Live, a tool call can pause the conversation until the result is back (BLOCKING), or the model can keep talking while the tool runs (NON_BLOCKING). A photo request can take 10+ seconds because a human must walk to the unit. NON_BLOCKING lets Ustaad say "take your time, flash on" meanwhile. Scheduling on the *response* (WHEN_IDLE: deliver the result when the model finishes speaking; SILENT: do not make it say anything about it) controls how the result is injected. SPEC: `request_media` is NON_BLOCKING + WHEN_IDLE; `save_profile_fields` is NON_BLOCKING + SILENT. Set `behavior` explicitly on every declaration because defaults differ between Live models.

*Signed URLs.* A time-limited URL that grants upload (PUT) or download (GET) of one object in Storage without credentials. The API mints it (`POST /api/media/upload-url`, 900 s), the phone uploads directly. The API never streams file bytes.

**Flow.**

```
agent -> request_media(kind, target, reason, framing_tip)  [NON_BLOCKING]
 tool: create request_id r_1, store pending request, push `media_request` frame
phone: opens camera sheet (title = request, framing tip), <input type=file accept=image/* capture=environment>
       resize 1600px JPEG -> POST /api/media/upload-url -> PUT -> WS media_ready{request_id, uri, kind}
server: on media_ready -> vision check "does this show <target>?" -> {matches_expected, findings, confidence, follow_up}
        send `media_result` (retake_reason when poor)
        deliver tool response to the agent (WHEN_IDLE)
rules: confidence < 0.6 -> follow_up with retake reason, max 2 retakes; media_cancel ends it
```

The pending-request table lives in the session (server) keyed by `request_id`; `media_ready` for an unknown or already-completed id is rejected. This also stops the model from reusing an old photo.

**From T09.** `RequestMediaIn` / `RequestMediaOut` already exist in `backend/models/tools.py`; `findings` is the same trimmed observation list as in T12. Open question to settle here: the G2 mock re-uses `request_id` `r_1` for the retake; if a retake should get a new id, change `seed/fixtures/live_session.jsonl` too. The server cannot find that fixture on Cloud Run (it is outside `backend/`, REVIEW-2026-10-11 §4), so `MOCK_LIVE=1` is local-only until that is fixed.

**Design rules.** The vision check is an injected `VisionClient`. Retake count is part of state. Retake reasons are in the worker's language (use the profile `lang`; the strings come from a small server-side table, not hard-coded English). Camera sheet copy from i18n.

**Tests.** Unit: fake vision returns 0.41 -> `retake_reason` set; second poor result -> stop asking and continue with a note; confidence 0.9 -> `matches_expected` true. WS test: `media_ready` for an unknown id returns `error{bad_request}`. Manual on phone: blur on purpose, get "Photo dhundhli hai", retake, continue (G2).

**Pitfalls.** Android camera intent can kill the PWA page in memory-poor phones, losing the WebSocket: rely on session resumption and persist the pending request. Large images over 4G: resize before upload. HEIC from iPhones: convert/resize via canvas to JPEG.

```
ID: T17 / M4   Owner: A   Branch: a/M4-request-media
Goal: request_media tool + WS media_request/media_ready flow + camera sheet + retake loop
Read: SPEC §6 (request_media row), shared/contracts/ws-events.md, backend/AGENTS.md, web/AGENTS.md
Done when:
- tests/unit/test_request_media.py passes (fake vision)
- confidence <0.6 returns follow_up with retake reason; max 2 retakes
- declared NON_BLOCKING, WHEN_IDLE
- on phone: request -> blurry -> retake reason -> clear -> continue
Don't touch: shared/contracts/, backend/agent/instruction.md
```

#### T18 Inventory tools, `/w/stock`, voice deltas (B, P1)

**Goal.** "Do capacitor use kiye" decrements stock by 2; repair checks stock first; low-stock badge.

**Tools.** `check_inventory(part)` BLOCKING; `update_inventory([{part, delta}])` SILENT. Firestore `workers/{wid}/inventory/{part_id}` with `name, aliases[], qty, min_qty, source`. REST `GET/PATCH /api/inventory` (PATCH body `{"deltas":[{"part","delta"}]}`).

**Steps.** (1) Part-name resolution: match against `name` and `aliases` (normalise case, spaces, "mfd"/"capacitor"); a small Flash fallback may map an unknown phrase to a part, but only returning an existing part id or "none" (never invent a part). (2) Delta update inside a Firestore transaction so qty never races; reject going below 0 or clamp and warn. (3) `low = qty <= min_qty`. (4) `stock` WS frame from the wrapper. (5) `/w/stock` list with qty steppers and a low badge.

**Design rules.** Pure `apply_deltas(items, deltas) -> items` separate from the Firestore transaction so it is trivially testable. Money integer rupees.

**Tests.** Unit: -2 on qty 5 gives 3; unknown part returns an error not a new part; low flag at threshold. Manual: voice "do capacitor use kiye" produces `stock` frame and the list changes.

**Pitfall.** The agent calling `update_inventory` twice for the same sentence: make deltas carry a client-supplied operation id (**Suggested (not yet in spec)**) or only allow stock updates tied to `close_job`/explicit confirmation.

```
ID: T18 / M7   Owner: B   Branch: b/M7-inventory
Goal: check_inventory/update_inventory tools, /api/inventory, /w/stock, voice deltas
Read: shared/contracts/rest.md, shared/contracts/firestore.md, backend/AGENTS.md, web/AGENTS.md
Done when: "do capacitor use kiye" -> qty -2 in a test; low-stock badge shows; make check passes
Don't touch: shared/contracts/, backend/agent/instruction.md
```

#### T19 WhatsApp webhook and the quote state machine (B, P0)

**Goal.** Send quote requests to 3 vendor phones, receive replies (text or voice), parse them, rank them. Under 2 minutes end to end.

**Concepts.**

*WhatsApp Cloud API.* Meta hosts a REST API. You POST messages to `/{PHONE_ID}/messages` with a bearer token. Incoming messages arrive as webhook POSTs.

*The 24-hour window.* You may send *free-form* messages to a number only within 24 hours after that number last messaged you. Outside the window you may send only pre-approved *templates*. This is why SPEC says vendor phones send "hi" before demos, with the `hello_world` template as fallback. Build `send_message()` so it chooses text if the window is open, else template.

*Webhook signature check.* Meta signs the raw body with your app secret (`X-Hub-Signature-256: sha256=<hmac>`). Compute HMAC-SHA256 over the **raw bytes** with `WA_APP_SECRET`, compare with `hmac.compare_digest`. Never parse JSON first and re-serialise. Anyone who knows your URL can POST fakes otherwise.

*Fast ack plus background.* Meta times out and retries when you are slow. Return `200` immediately and process in a background task.

*Idempotency.* Each inbound message has an ID (`wamid`). The doc `wa_messages/{wamid}` is created first; if creating fails because it exists, drop the delivery.

**Quote state machine.** Per vendor: `CREATED -> SENT -> PARSING -> QUOTED -> CONFIRMED`; `CLARIFY` (one follow-up allowed); `EXPIRED` after 30 min; `DECLINED`. Request-level `status`: `open|approved|expired`.

```
            send ok          vendor reply          parse ok
 CREATED ---------> SENT ----------------> PARSING ---------> QUOTED --approve--> CONFIRMED
                      |                       |  low confidence
                      | 30 min                +--------------> CLARIFY (once) -> PARSING
                      v                       | "nahi hai"
                   EXPIRED                    +--------------> DECLINED
```

**Steps.**
1. `wa/signature.py`: verify function; `wa/client.py`: `send_text`, `send_template`, behind an interface so tests use a fake.
2. Webhook GET (verify) and POST (verify signature -> 200 -> `BackgroundTasks`).
3. Handler: extract message, dedupe on `wamid`, find the open quote for that vendor (phone hashed: store `from_hash`, not the number), branch on type: text -> parse; audio -> download media via Graph API, convert/transcribe (reuse the T13 transcriber), then parse.
4. Parser: Flash returns `{price_inr, available, eta, confidence}` (§7). Price integers only. Low confidence -> CLARIFY with a short question; second failure -> leave for manual.
5. `find_vendors(part, pincode)`: saved vendors plus Places API (New) results. `request_quotes(job_id, part, specs, vendor_ids)` NON_BLOCKING: creates docs, sends messages, returns `quote_request_id`.
6. `get_quotes` ranks by availability, then price, then distance; `approve_quote` sets CONFIRMED and sends confirmation messages (and a polite decline to the others, optional).
7. An expiry sweep: on each poll compute `now > expires_at` rather than relying on a timer (serverless instances can disappear).

**Design rules.** The transition table is one pure function; all handlers call it. Vendor phones (`wa_phone`, E.164) never committed to git; stored in Firestore/Secret Manager only. Raw webhook bodies are server-only.

**Tests.** Unit: signature valid/invalid; duplicate `wamid` processed once; each legal transition and an illegal one; parser fixtures (text "3400 rupay, 45 min mein", "nahi hai", a voice transcript). Manual: 3 team phones reply, one by voice; `quotes` frame updates 3 times (G3).

**Pitfalls.** Using `request.json()` before computing the signature. Forgetting that the test number can only message the 5 registered recipients. Temporary Meta token expiring (use the system-user token). Webhook URL pointing at `dev` while testing `demo`. Voice-note media must be downloaded with the token via a media-id lookup, not a public URL.

```
ID: T19 / M8   Owner: B   Branch: b/M8-quotes
Goal: WhatsApp webhook (verify + signature + idempotent), quote state machine, find_vendors (Places), request_quotes/get_quotes/approve_quote
Read: SPEC §7 (quotes), shared/contracts/firestore.md, shared/contracts/rest.md, backend/AGENTS.md
Done when:
- tests: signature, wamid dedupe, state transitions, parser fixtures
- 3 team phones get requests on dev; replies (one voice) parsed and ranked
Don't touch: shared/contracts/, backend/agent/instruction.md
```

#### T20 Memory Bank: preload and save (A, P2)

**Concept.** *Memory Bank* stores soft facts extracted from conversations ("prefers Hindi", "weak on inverter PCB diagnosis") across sessions, on an Agent Engine instance (`AGENT_ENGINE_ID`, created by `make agent-engine`). *PreloadMemoryTool* injects relevant memories at the start of a turn. Structured facts (inventory, jobs) stay in Firestore; Memory Bank is for soft facts only.

**Steps.** Configure the memory service with the engine ID; add PreloadMemoryTool to the agent; at session end call the add-session-to-memory path; test that a second session recalls language and a weak area. Do this only after M2 to M5 pass (Should). **Tests.** Fake memory service in unit tests; one manual two-session check. **Pitfall.** Memory is per user id; use the worker id consistently, and demo workers must not leak into each other.

```
ID: T20 / S3   Owner: A   Branch: a/S3-memory
Goal: Memory Bank preload + save at session end
Read: SPEC §6 (Memory), backend/AGENTS.md
Done when: 2nd session recalls language and a weak area (manual); unit test with fake memory service
Don't touch: shared/contracts/, backend/agent/instruction.md
```

---

### Wed Oct 14: finish features, integration at 21:00 (T21 to T26)

#### T21 Onboarding interview in 4 languages (A, P1)
**Goal.** Language tile, then 6 spoken questions; profile card fills live (G1: trades, brands, pincode, experience, stock, vendors). **Tool.** `save_profile_fields(partial profile)`, NON_BLOCKING + SILENT: the agent keeps talking while fields are saved and a `profile_update` frame animates the card. **Steps.** Onboarding variant of the instruction (Suggested: a section in `instruction.md` activated when `onboarding_done` is false); write answers as partial updates (merge, don't replace); mark `onboarding_done` after the last field; hi and te recorded sessions as fixtures (`live_session_g1.jsonl`). **Pitfalls.** Spoken numbers ("do-ek-teen-sunya-ek" for a pincode): ask the model to emit digits and validate 6 digits server-side; brand names transcribed oddly ("Voltas" as "Voltaas"): normalise against a brand list. **Tests.** Tool unit test; replay test of `profile_update` frames. **From T38.** `trades` is the appliance list: 1 to 3 values, no duplicates, from `ac`, `fridge`, `washing_machine`, `led_tv`, `microwave`, `geyser`, `fan_cooler`, `other` (firestore.md). No new profile field and still 6 questions. `save_profile_fields` validates; if the worker names more than 3, Ustaad asks for his top 3 and never truncates silently. The profile card shows the values as chips, with strings in all five i18n files. Tests: 4 values rejected; 3 accepted; an unknown value rejected; duplicates rejected; naming 4 appliances leads to a "pick your top 3" turn.
```
ID: T21 / M1   Owner: A   Branch: a/M1-onboarding
Goal: voice onboarding, 6 questions, live profile card, hi + te
Read: SPEC §3 M1, ws-events profile_update, GOLDEN_PATHS G1
Done when: G1 passes in hi and te; save_profile_fields unit test; pincode validation test;
           trades validation tests (4 rejected, 3 accepted, unknown rejected, duplicates rejected); 4 named -> "top 3" turn
Don't touch: shared/contracts/
```

#### T22 `close_job` -> card with photo, stock decrement (A, P1)
**Goal.** "Ho gaya, capacitor badla" closes the job, drafts a new fault card with photo, decrements stock. **Steps.** `close_job(job_id, outcome, parts_used, fix_summary)` BLOCKING: reject if any gate open (callback also); build a card draft using the close-job prompt (§7), attach `photo_uri` from the last relevant job media, mark the card `source.kind` as a job closure and `review_status` pending (**Inferred**: closure cards need review); call `update_inventory`; set job `closed`, `closed_at`; emit `job_closed{job_id, card_id}`. Calling the stock tool from `close_job` crosses lanes (B's tool): use B's pure function through the same interface, don't copy it. **Tests.** G4 fixture `close_job.json`; closing with an open gate is rejected; stock -1. **Pitfall.** Double close.
```
ID: T22 / M9   Owner: A   Branch: a/M9-close-job
Goal: close_job tool: job log, draft fault card with photo, stock decrement, job_closed frame
Read: SPEC §6, shared/contracts/firestore.md, GOLDEN_PATHS G4
Done when: G4 passes (fixture + unit); open gate rejects close; second close is idempotent
Don't touch: shared/contracts/, docs/SAFETY.md
```

#### T23 Quotes card in job screen + approve (B, P0)
**Goal.** On `/w/job/:id` show the quotes list as replies arrive, one-tap approve. **Steps.** Component reading `quotes` WS frames (and polling `GET /api/quotes/{qrid}` every 2 s while visible as backup); Copper `#A9592D` for prices; "Approve quote" button -> `POST /api/quotes/{qid}/approve` -> toast "Quote approved"; badge for `from_voice`. Strings in i18n, built on A's base components. **Tests.** Component test with `quotes.json`; Playwright screenshot at 360 px. **Pitfall.** Re-render flicker when the list re-sorts; stable keys by `quote_id`.
```
ID: T23 / M8   Owner: B   Branch: b/M8-quotes-ui
Goal: quotes card in job screen with live updates + approve
Read: DESIGN.md, ws-events (quotes), playbooks/ui-pass.md, web/AGENTS.md
Done when: G3 passes on a phone; screenshots 360 + 1280 in PR
Don't touch: shared/contracts/, backend/agent/
```

#### T24 Dashboard: knowledge base, import progress, review queue (B, P1)
**Goal.** `/d/knowledge` list of fault "tags" in rows; `/d/import` waveform list turning into tags with live counts; review queue for low-confidence cards (approve/reject via `PATCH /api/fault-cards/{id}`). **Steps.** Poll `GET /api/imports/{id}` every 2 s; audio playback from the card's audio link (signed GET URL); show speaker, date, confidence. **Tests.** Fixture-driven component tests; G5 on laptop. **Pitfall.** Autoplay of audio; signed URL expiry (refresh on 403).

**From T08 (Oct 16).** The demo group's photos are AI-generated or taken from public posts (PRODUCT.md, honest demo). Wherever `/d/import` or `/d/knowledge` shows a photo from that import, show a label on it (i18n strings): "AI-generated image" or "Image from a public post", per the list in `seed/voice_note_script.md`; and say once on the import screen that the voice notes are real and the photos are not.
```
ID: T24 / M6   Owner: B   Branch: b/M6-dashboard
Goal: /d/knowledge, /d/import live progress, review queue
Read: DESIGN.md, playbooks/ui-pass.md, rest.md
Done when: G5 passes on laptop with the demo export
Don't touch: shared/contracts/, backend/agent/
```

#### T25 Seed data, clusters, area map (B, P2)
Detailed in §8.7. **Done when:** cluster visible, badged "Demo data".
```
ID: T25 / S2   Owner: B   Branch: b/S2-seed
Goal: seed script: ~50 synthetic cards (to total ~80), 200 jobs, 3 workers; compute-clusters job; /d/area map
Read: SPEC §10, shared/contracts/firestore.md
Done when: seed is deterministic (fixed seed); cluster visible; all seeded rows labelled
Don't touch: shared/contracts/, docs/SAFETY.md
```

#### T26 Integration gate (both, P0)
**Goal.** G2 and G3 end to end on a real phone against `dev`, 21:00. **Do.** Run the G2 script from GOLDEN_PATHS with real photos, then G3 with the three team phones. Log pass/fail and timings in `docs/STATUS.md`. **If it fails.** Fix on Thursday morning; do not add features. **Pitfall.** Testing only from a laptop emulator.

**From T17 (phone tests on dev, Oct 15).** G2 sends real photos, so check two things T17 could not close on the laptop:
1. *Bracketed notes spoken aloud.* Twice Ustaad said "[Photo from the worker …]" aloud, in English, after a photo. The instruction line was reworded (commit cd1d3be), but the laptop never reproduced it (0/24 runs, old and new wording), so only the phone shows whether it is fixed. Send at least 3 photos (his own and requested) and note any bracket or English label in Ustaad's words.
2. *Photo paths not yet tried on a phone:* the capacitor gate (`G_CAP_DISCHARGE`), closing the camera sheet with ✕, the retake limit (after 2 retakes Ustaad continues with a note), and all of it on 4G.
```
ID: T26   Owner: both   Branch: none
Goal: G2 + G3 on a real phone, dev
Read: GOLDEN_PATHS
Done when: both pass; logged in STATUS.md, with the two T17 checks
Don't touch: new features
```

---

### General-appliance tier (T38 to T41)

Ustaad's knowledge is all AC. This tier makes it safe and useful for fridge, washing machine, LED TV, microwave, geyser and fan/cooler, with no web search and no extra model call in a voice turn. Design: SPEC §6 (appliance types, source tiers, general steps) and SAFETY.md (hazard tagger, default gate, hard stops, backstop). The decisions are made; do not re-decide them. It is first in the cut order: the never-cut list must work for AC before any of it is switched on. Lane A's tool code is in T12, T16 and T21 (their "From T38" notes).

#### T38 Contracts and docs for the general tier (A, P2)
Done: contracts PR #15 and the docs PR that added this section. Nothing to build.

#### T39 Instruction tiers, caption backstop, chip, stop strings (A, P2)

**Goal.** The last small PR of the tier: what the worker hears and sees.

**Steps.**
1. Propose the source-tier text for `backend/agent/instruction.md` (human-owned: put the proposed text in the PR; A approves). Keep it short. It must say: tiers 1 and 2 are cited aloud; tier 3 only when both return nothing, said aloud as general guidance with no verified source; tier 3 never gives an error-code meaning, a component value or model-specific wiring, and instead says the code is not in its sources and asks to see the manual page or wiring sticker (the T37 flow if built); prefer checks the worker can prove with a photo; in every tier say a repair step only after `next_step` has returned it; photos only.
2. Caption backstop: run T16's tagger over each of Ustaad's final captions; a stop match sends a `safety_stop` frame. It fires after the words begin, so name it a backstop in code, tests and docs, never a gate, and do not add it to the bypass tests.
3. Source chip: a "General guidance" variant for `source.kind: general`, with no audio button, styled per DESIGN.md.
4. Stop screen: full-screen red with fixed text per reason (`refrigerant`, `microwave_hv`, `crt`, `geyser_open`) in all five i18n files. No audio clip.
5. Write the G8 mock fixture `seed/fixtures/live_session_general.jsonl`. Its step is a check the worker can prove with a photo, with no error-code meaning, component value or wiring.
6. Manual instruction check, written into STATUS.md: 5 out-of-card questions in Hindi, one each for washing machine, fridge, LED TV, geyser and microwave. Each answer is labelled general, invents no error-code meaning, and asks to see before guessing.

**From T17 (phone and laptop tests, Oct 15): general steps that need the power on.** Twice the Live model proposed a check that needs live supply right after the mains-off photo had passed: the step "पावर सप्लाई और एमसीबी चेक करें कि सप्लाई आ रही है या नहीं" (check at the MCB whether supply is coming; tagged `none`, job `j_p5a`), and, in a laptop run, "check the voltage at the socket" once the MCB is off. The tagger cannot catch this: a general job already needs `G_MAINS_OFF` before every step, and that gate had passed. So step 1's tier-3 text must also say: general guidance never proposes a step that needs the power on (voltage, supply or live tests); such checks come only from a card or manual, otherwise Ustaad says a qualified electrician should check. Propose the matching line for `docs/SAFETY.md` in the PR (human-owned; A approves) and add it to step 6's manual check: one question that invites a live test, answered without one.

**Pitfalls.** Calling the backstop a gate; a chip label or stop text hard-coded outside `web/src/i18n/`; adding a model call to classify captions (the tagger is keyword rules only).

```
ID: T39   Owner: A   Branch: a/T39-general-tier-final
Goal: instruction source tiers (proposed text), caption backstop, "General guidance" chip, stop-screen strings
Read: docs/SPEC.md §6 (source tiers), docs/SAFETY.md, docs/DESIGN.md, shared/contracts/ws-events.md (step_card, safety_stop),
      docs/GOLDEN_PATHS.md G8, backend/AGENTS.md, web/AGENTS.md, docs/playbooks/ui-pass.md
Done when:
- a final Ustaad caption that matches a stop row produces a safety_stop frame (unit test, no model)
- the chip renders for source.kind "general" with no audio button; screenshots at 360 and 1280
- each stop reason has its text in en, hi, te, ta, bn
- G8 replays from live_session_general.jsonl
- the 5-question Hindi check is recorded in docs/STATUS.md
Don't touch: backend/agent/instruction.md without A's approval; backend/agent/callbacks.py; shared/contracts/; Lane B code
Out of scope: web search, video, any extra model call, audio on stop screens
```

#### T40 Card extraction sets `appliance_type` (B, P2)

**Goal.** Every imported card carries an appliance type, so search can filter on it. **Steps.** The card-extraction prompt (T15, §7.4) sets `appliance_type` to one of the schema values from what is said in the thread; when the type is unclear the card goes to the review queue (`review_status: needs_review`) instead of guessing. Existing cards stay valid, so there is no backfill. **Pitfall.** Guessing `split_ac` for every unclear thread because most of the data is AC.

```
ID: T40   Owner: B   Branch: b/T40-card-appliance-type
Goal: the extraction prompt sets appliance_type; an unclear type goes to the review queue
Read: docs/SPEC.md §4, shared/contracts/fault_card.schema.json, backend/AGENTS.md
Done when:
- extraction test with recorded responses: a non-AC thread gets its type
- an unclear thread gets review_status needs_review
Don't touch: shared/contracts/, backend/agent/, docs/SAFETY.md
Out of scope: backfilling existing cards; manual metadata in Agent Search
```

#### T41 `search_fault_cards` appliance filter and relevance floor (B, P2)

**Goal.** A TV question never gets an AC card, and an unrelated question gets nothing instead of a weak match. **Steps.** `search_fault_cards` takes an optional `appliance_type`. Filter in code after the vector query: fetch the top 20, drop other types, return the top 5. Do not add a Firestore index before the freeze. Return an empty list when the best match is below a named relevance-floor constant; the value is set in T15 from real embeddings, and until then it is a placeholder marked as such. The REST list endpoint takes the same optional filter (rest.md). **Pitfall.** Filtering before the vector query, which needs a new composite index.

```
ID: T41   Owner: B   Branch: b/T41-search-appliance-filter
Goal: optional appliance_type filter in code after the vector query; empty list below a named relevance floor
Read: docs/SPEC.md §6, shared/contracts/rest.md, shared/contracts/fault_card.schema.json, backend/AGENTS.md
Done when (fake embedder, no network):
- an "LG TV" query never returns AC cards
- an unrelated symptom returns an empty list
- the Voltas query still returns Ramesh's card
Don't touch: shared/contracts/, backend/agent/, docs/SAFETY.md
Out of scope: a new Firestore index; manual metadata in Agent Search
```

---

### Thu Oct 15: harden (freeze 18:00) (T27 to T30)

#### T27 Demo-safe cache, rate limits, "Try the demo" (A, P0)

**Goal.** A judge on an unknown phone and network must see the golden path work even if a model is slow.

**Concepts.** *Caching by input hash:* hash the normalised input (text or audio digest + job context + language) to a key; store the response in `demo_cache/{hash}` (`request_hash, response, model, created_at`). *Fallback after 6 s:* race the live call against a timer; if 6 s pass or the call errors and a cache entry exists, serve it. *Rate limits:* 20 req/min per IP on `/api/chat` and `/ws/live`, 3 concurrent Live sessions (SPEC §5): protects credits and keeps the demo alive under judge load.

**Steps.**
1. `DEMO_SAFE=1` env flag (shown in `/healthz`).
2. A small `DemoCache` interface (`get(hash)`, `put(...)`) with a Firestore implementation (db `demo`) and an in-memory fake.
3. Warm it: a script runs the golden paths once against real models and stores responses (the cache is generated from real model output, never typed by hand, to keep the demo honest).
4. `POST /api/demo/session`: returns a signed 24 h token, the seeded Hindi worker (`w_hi_demo`) and `ws_url`.
5. "Try the demo" button on `/w/start`: calls it, no login. Sample photos shipped as assets so a judge without an AC can still run G2.
6. Rate limiter: in-process token bucket is enough for one instance with `min-instances` 1; note Cloud Run can run several instances, so keep per-IP limits simple (Suggested: accept that limits are per instance).
7. Live sessions: counter with a semaphore (3); the 4th gets `error{rate_limited}`.

**From T11 (phone test on dev, Oct 14).** Two follow-ups found while testing the Live bridge; do them here because both touch the Live-session limit:
1. *Close dead sockets.* When a phone loses its network, the server keeps that connection, and its Live session, open until TCP gives up (13 s in the test, can be longer). Each one counts against the 3-session limit, so a judge's dropped connections could lock out the next judge. The client already pings every 20 s: in `app/ws_live.py`, close a connection that has sent nothing for 45 s (a named constant), and release its semaphore slot. Test with a fake clock or a short constant: a silent client is closed; a pinging one is not.
2. *Faster first turn after a reconnect.* The mic stays disabled until the new session's `session_ready`, and opening a Live session takes 2 to 4 s, so after a network change the worker waits. Let the mic be pressed while `reconnecting`: buffer up to about 5 s of PCM in `liveClient.ts` and send it, inside `ptt start`/`end`, once the socket is open (drop it if the reconnect fails). Recheck on 4G only: in the Wi-Fi test the phone reconnected 4 times in 3 minutes, most likely from switching networks.

**From T17 (Oct 15).** Photo checks (Flash) take 5–6 s, but about 1 in 4 took ~30 s and hit `VISION_TIMEOUT_S` (30 s), so the phone asked for the photo again. While a check runs, show "still checking" on the camera sheet after ~10 s (i18n string), and let the demo cache answer the shipped sample photos so a judge never waits on a slow check.

**From T08 (Oct 16).** "Try the demo" ships sample photos that are AI-generated or taken from public posts (the team had no faulty units to photograph); each shows its label, "AI-generated image" or "Image from a public post" (i18n). The G2 safety-gate photo in the video is a real photo of our own MCB switched off.

**Design rules.** The cache sits behind one wrapper used by `/api/chat` and the tool-response path; it never changes the *safety* behaviour: a cached response for a hazardous step still goes through gate logic (cache before the model, not before the safety layer).

**Tests.** Unit: same input hits cache; slow fake model plus cache hit returns after the timer; no cache entry and a slow model returns the slow result. Manual: incognito phone, backend models slowed (add an artificial delay env), G2 still completes.

**Pitfalls.** Cache key unstable (timestamps in the input); caching errors; serving a cached answer for a different language; judges hitting the 3-session limit during evaluation (consider raising for the demo service and recording the decision).

```
ID: T27 / M10   Owner: A   Branch: a/M10-demo-safe
Goal: demo-safe cache (hash key, 6 s fallback), rate limits (20/min/IP, 3 Live), Try the demo, /api/demo/session
Read: SPEC §10, SPEC §5, shared/contracts/rest.md (demo/session), backend/AGENTS.md
Done when: incognito phone completes G2 with models artificially slowed; unit tests for cache + limiter;
           a silent connection is closed after 45 s and frees its Live slot; mic usable while reconnecting
Don't touch: shared/contracts/, docs/SAFETY.md, backend/agent/callbacks.py
```

#### T28 UI polish pass (B, P1)
Use `docs/playbooks/ui-pass.md` on each screen: plan in 5 to 8 lines, check against DESIGN.md's generic-defaults table, build with tokens and i18n only, screenshot 360 and 1280, fix, `make check`. Quality floor: 360 px, 48 px targets, visible focus, `prefers-reduced-motion` turns the code-readout blink into a single fade, Hindi/Telugu render without fallback boxes, errors say what happened and what to do, seeded data labelled. **Pitfall.** Colour literals sneaking in. 
```
ID: T28   Owner: B   Branch: b/T28-ui-polish
Goal: UI pass on every screen
Read: DESIGN.md, playbooks/ui-pass.md, web/AGENTS.md
Done when: screenshots at 360 and 1280 in the PR for each route
Don't touch: shared/contracts/, backend/
```

#### T29 Golden tests and quality bar (A, P1)
Covered in §10. Produce the numbers: latency p50s, 6/6 photos, import accuracy (from B's gold set), quotes time, 0/10 bypasses. Put them in `docs/STATUS.md`; the deck uses them.
```
ID: T29   Owner: A   Branch: a/T29-golden
Goal: make golden against real models; measure the SPEC §10 targets and report actuals
Read: GOLDEN_PATHS, SPEC §10
Done when: numbers (actual, not target) in docs/STATUS.md
Don't touch: shared/contracts/
```

#### T30 Feature freeze, tag `v1-rc`, deploy demo (both, P0)
At 18:00 stop merging features. Merge only fixes. `git tag v1-rc`, `make deploy-demo`. Set `min-instances` 1 on demo. Run all golden paths on the demo service. Anything not working gets cut or hidden, not rushed.
```
ID: T30   Owner: both   Branch: none (tag)
Goal: freeze, tag v1-rc, make deploy-demo
Read: WORKFLOW
Done when: demo service on v1-rc; golden paths pass on it
Don't touch: features
```

---

### Fri Oct 16 to Sat Oct 17: ship (T31 to T35)

- **T31 Shoot video (both, P0).** Real AC, two phones, screen capture. Plan beats from the four moments and GOLDEN_PATHS order (G1 quick, G2, G6 Telugu clip, G3, G4, G5). Shoot a second take of each. Record clean audio. Show measured numbers on screen.
- **T32 Deck, README, architecture image (B, P0).** 10 slides, PDF in `docs/`. Lead with the differentiators in PRODUCT.md. Include the §2.1 diagram redrawn cleanly and the measured numbers. README: what it is, link, how to run, architecture, licence, honest note on synthetic data.
- **T33 Edit video (A, P0).** Under 2:58, subtitles in English, uploaded unlisted (YouTube/Vimeo) plus a Drive copy.
- **T34 Final demo deploy and link check (A, P0).** Walk the WORKFLOW checklist in incognito on a phone and a laptop: app link, repo public, video public, deck opens, no secrets in repo.
- **T35 Submit by 21:00 IST (both, P0).** Submit early, e.g. by 18:00; screenshot the confirmation. All materials in English; theme named: Future of Work and Enterprise Productivity.

```
ID: T33   Owner: A   Branch: none
Goal: edit video, subtitles, narration, <2:58, upload unlisted + Drive copy
Read: PRODUCT.md
Done when: link opens logged out; duration <2:58
Don't touch: code except fixes
```

---

## 6. The agent in depth

### 6.1 One agent, two modes

`build_ustaad(model)` returns one ADK agent. The model argument is the only difference: Live runs `runner.run_live()` with `LIVE_MODEL`; text runs `runner.run_async()` with `FLASH_MODEL` (used by `/api/chat`). Same instruction, same tools. **Why one agent:** two agents drift apart; every behavioural fix would be done twice.

```python
def build_ustaad(model: str, *, deps: Deps) -> Agent:
    return Agent(
        name="ustaad",
        model=model,
        instruction=load_text("agent/instruction.md"),
        tools=[wrap(t, deps) for t in ALL_TOOLS],      # thin wrappers over pure functions
        before_tool_callback=safety_callback(deps),
    )
```

*(Shape only; check ADK's current constructor.)* Putting `deps` in makes the agent testable with fakes.

### 6.2 The tools, and what the Live scheduling means

| Tool | What it does | Behaviour | Why that behaviour |
| --- | --- | --- | --- |
| save_profile_fields | store parts of the profile | NON_BLOCKING, SILENT | Saving must not interrupt the interview or make the model comment |
| identify_appliance | read nameplate/error photo | BLOCKING | Next sentence depends on the answer |
| request_media | ask for a photo/clip | NON_BLOCKING, WHEN_IDLE | Human takes time; model can say "flash on karo"; result delivered when it is idle |
| search_fault_cards | recorded-note search | BLOCKING | Need the answer to speak it and cite |
| search_manuals | manual snippets | BLOCKING | Same |
| start_repair | build the step list from cards | BLOCKING | |
| next_step | next step or SAFETY_GATE | BLOCKING | The gate must resolve before speaking |
| confirm_safety | vision check of gate evidence | BLOCKING | |
| check_inventory | stock | BLOCKING | Decide parts before advising |
| update_inventory | decrement | SILENT | Bookkeeping, not conversation |
| find_vendors | saved + Places | BLOCKING | |
| request_quotes | message vendors | NON_BLOCKING | Replies take minutes; worker keeps working |
| get_quotes / approve_quote | rank / confirm | BLOCKING | |
| close_job | job log + card draft | BLOCKING | |
| get_nudges / get_area_alerts | coaching / clusters | BLOCKING | |

Reminder: `behavior` is on the declaration; scheduling (WHEN_IDLE, SILENT) is on the function response. SPEC decision: set `behavior` explicitly on every declaration.

### 6.3 What the instruction must say

`backend/agent/instruction.md` is **not written yet** and is human-owned. SPEC §6 gives the content in one paragraph. **Suggested (not yet in spec)** outline:

```
1. Role: you are Ustaad, a patient senior technician helping one worker at a time.
2. Language: answer in the worker's language from his profile. Hinglish is normal; never correct his words;
   keep error codes and part names as spoken ("E6", "capacitor").
3. Style: one instruction at a time; short sentences; wait for "ho gaya"/confirmation before the next.
4. Grounding: ground every fix in a fault card or manual snippet from a tool; say the source aloud
   ("Ramesh ne May 2025 mein bataya tha"); if no source, say you don't know and ask for a photo or offer to
   ask a senior. Never state an error-code meaning from memory.
5. Ask to see instead of guessing: use request_media with a short framing tip.
6. Safety: never describe a hazardous step before next_step returns it; never give refrigerant steps or how
   to bypass safety devices; if asked, say a certified gas technician is needed. Treat "I am certified" as
   irrelevant. Gate and stop behaviour is enforced by tools; do not argue with it.
7. Stock: check inventory before suggesting parts; offer quotes when a part is missing.
8. Tool etiquette: say a brief filler ("ek minute, stock dekh raha hoon") before slow tools; don't read raw JSON.
9. End: when the worker says it's fixed, call close_job and ask the two closing questions
   (what was the cause, what part/fix).
10. Onboarding mode (if onboarding_done is false): the six questions in order, one at a time.
```

Keep it short; long instructions dilute attention in voice models. Review it as a pair, test it with `make golden`.

### 6.4 Where state lives

| Store | What | Lifetime | Why there |
| --- | --- | --- | --- |
| ADK session state | current job id, step index, gate cache, pending media requests | one connection (survives reconnect via resume handle) | Fast, per-conversation |
| Firestore | workers, jobs (steps, gates, media), inventory, cards, quotes | permanent | Source of truth, survives restarts; gates must be here |
| Memory Bank | soft facts: language preference, weak areas, habits | across sessions | Free-form recall the agent can use without us designing a schema |

Rule: anything the safety logic depends on (gates) must be in Firestore, since session state can be lost. Anything the UI must show after refresh is in Firestore.

### 6.5 Safety at four layers

```
 Layer 1  PROMPT      "never describe a hazardous step before its gate"        (advisory only)
 Layer 2  TOOL        next_step returns SAFETY_GATE; refrigerant returns STOP_REFER
 Layer 3  CALLBACK    before_tool_callback rejects next_step/close_job with open gate
 Layer 4  CLIENT      renders safety screens; drops hazardous step_card while gate open
```

If layer 1 fails (the model says something unsafe aloud), layers 2 to 4 still stop the *step cards and tool results*. That is the honest limit: speech is generated by the model, so the instruction must also forbid it and the Live model must not be given hazardous instruction text before the gate passes (it only sees a step once `next_step` returns it).

---

## 7. Prompts that still need writing

Every item below is **Suggested (not yet in spec)** except where the doc is cited. Each prompt is a versioned file; each output is validated by Pydantic; each has a way to evaluate. General skeleton for all structured prompts:

```
ROLE:   one line
INPUT:  what you receive, labelled
RULES:  numbered, include "use only what is in the input; if unsure say null; keep Hinglish/codes/part numbers verbatim"
OUTPUT: JSON matching the schema (use the SDK's response schema / structured output)
```

| # | LLM call | Where | Model | Input | Output schema |
| --- | --- | --- | --- | --- | --- |
| 1 | Transcription | T13 | Flash | FLAC audio | `Transcript{text, language, confidence}` (SPEC §4) |
| 2 | Photo description | T13 | Flash vision | image | `PhotoDesc{summary, visible_text[], objects[]}` |
| 3 | Thread grouping | T13 | Flash | messages in time order | `Threads{groups: list[list[msg_id]]}` |
| 4 | Card extraction | T15 | Flash | one thread | `FaultCardDraft` (per fault_card.schema.json) or `null` |
| 5 | identify_appliance | T12 | Flash vision | image | `IdentifyOut{brand, model, series, type, error_code, confidence, observations}` |
| 6 | request_media check | T17 | Flash vision | image + expected target | `RequestMediaOut{media_uri, matches_expected, findings, confidence, follow_up}` |
| 7 | Gate photo checks | T16 | Flash vision | image + gate | `GateCheck{passed, reason, confidence, reading_volts?}` |
| 8 | Vendor reply parsing | T19 | Flash | reply text/transcript | `VendorReply{price_inr, available, eta, confidence}` |
| 9 | close_job card draft | T22 | Flash | job log + two answers | `FaultCardDraft` |
| 10 | Onboarding | T21 | Live | speech | in the Live instruction; calls `save_profile_fields` |

### 7.1 Transcription
```
ROLE: You transcribe a short WhatsApp voice note from an Indian AC technician.
RULES: 1 Keep Hindi/English/Telugu mix as spoken, in the script the speaker used (Roman for Hinglish).
       2 Write error codes (E6, F1...), model numbers and part names exactly as heard; do not translate or expand.
       3 If a part is unintelligible write [unclear], never guess. 4 confidence 0-1 for the whole note.
OUTPUT: {text, language, confidence}
```
**Evaluate.** Hand-correct 10 notes; compute word error roughly by eye; check *code and part tokens* are right in at least 90%. Silent notes must give low confidence.

### 7.2 Photo description
Ask for a one-sentence factual description, any readable text (model numbers, code on display) and objects. Rule: describe only what is visible. **Evaluate.** 10 photos: is the visible text copied correctly.

### 7.3 Thread grouping
Input: all messages in time order, each with its id, speaker, time and minutes since the previous message. Task: group them into threads, one per fault: question → answers → outcome. A reply hours later still belongs to its question; a new question starts a new thread even minutes after the last. The input holds only eligible messages (T13 step 4: system and "This message was deleted" lines are already removed), and every input id must appear in exactly one thread. Rule: output only message ids; never rewrite messages. **Evaluate.** Gold set of threads (§8.8); count correct groupings.

### 7.4 Card extraction (the central prompt)
```
ROLE: You turn a technician chat thread into one fault card, or null.
RULES: 1 A card exists only if a fix or conclusion is stated. Unanswered questions -> null.
       2 Use only what people said or what photos show. Never add an error-code meaning, step or part not in the thread.
       3 Name sources: speaker first name, message ids used.
       4 Each step has hazard: none | HV | capacitor | refrigerant. Anything with gas charging, leak repair,
         brazing or pressure work is refrigerant. Anything touching a capacitor is capacitor.
       5 confidence 0-1: low if the speaker was unsure, the audio unclear, or people disagreed.
OUTPUT: FaultCardDraft JSON or null
```
**Evaluate.** On the gold set: card/null decision correct, brand+code correct, cause correct, hazard not lower than gold. A hazard *under*-estimate is a bug; an over-estimate is acceptable.

### 7.5 identify_appliance
Rules: read what is printed; for the code, copy the characters on the display; if not legible, `confidence` low and fields null. Never infer meaning. **Evaluate.** 6/6 golden photos; plus a few negative photos (a wall) must return low confidence.

### 7.6 request_media check
Input includes the *expected target* ("Outdoor PCB, capacitor ke paas") and the framing tip. Output `follow_up` is a one-line retake reason in the worker's language when `confidence < 0.6` (SPEC: see request_media row). **Evaluate.** Good photo, blurry, wrong object, too dark: right decision on each.

### 7.7 Gate photo checks
Two separate prompts, one per gate. G_MAINS_OFF: "Is the MCB/isolator visibly in the OFF position, or is the unit's plug visibly removed?" G_CAP_DISCHARGE: "What does the multimeter display read across the capacitor terminals, and is it DC volts?" Return the number. The *code* compares the number to 5 V and the confidence to 0.7 (SAFETY.md); the model never decides pass/fail alone for the capacitor gate. **Evaluate.** SAFETY tests 3 and 5, plus ambiguous photos (a switch half-visible): must fail closed.

### 7.8 Vendor reply parsing
Input: text or transcript ("3400 rupay, aadhe ghante mein pahunch jayega", "nahi hai"). Output integers for price, `available` bool, eta string, confidence. Rule: if price is missing or ambiguous (two numbers), null and low confidence so the state machine goes to CLARIFY. **Evaluate.** 15 hand-written replies including Hindi number words and a voice transcript.

### 7.9 close_job card draft
Input: the job record (appliance, code, steps done, photos, parts used) and the worker's two answers. Output a card draft with `review_status` pending and the job's photo. Rule: describe only what the job record and answers say. **Evaluate.** G4 produces a card whose cause and fix match what the worker said.

### 7.10 Onboarding
Part of the Live instruction (§6.3). Six questions in order. Each answer triggers `save_profile_fields`. **Evaluate.** G1 in hi and te: all six fields land correctly.

---

## 8. The WhatsApp group knowledge data: how to create it

### 8.1 Three different datasets: do not mix them up

| Dataset | What it is | Size | Real or synthetic | Used for | Where |
| --- | --- | --- | --- | --- | --- |
| **Demo export** | A real WhatsApp group "AC Technician Noida" that you and consenting friends record, then export | ~30 voice notes, ~40 texts, ~10 photos | **Real data in the real export format**; the faults are staged, content from real manuals | The import demo (G5, M6), the cards that G2 retrieves | `seed/whatsapp_export/` (see §8.5 decision) |
| **Synthetic cards and jobs** | Generated by a script | ~50 cards (to make ~80 total), 200 jobs, 3 workers, 15 Noida/Ghaziabad pincodes | **Synthetic**, labelled "Synthetic"/"Demo data" (`seeded: true`) | Dashboard fullness, cluster map (S2) | generated in T25 |
| **Unit-test fixture** | Tiny hand-built export | 3 to 5 messages, 1 to 2 tiny opus files or stubbed transcripts | Hand-made | `make test` for the parser and pipeline | `seed/whatsapp_export_small/` |

Do not let synthetic data pose as real. Do not use the large demo export in unit tests (slow, needs models).

### 8.2 Golden rules

1. **Meanings only from real service manuals.** Download the PDFs for the three brands (Voltas, Daikin, LG) first. Fill the 15-row table in `voice-note-script.md` *before* recording. Never invent error codes. No manual page, no row.
2. **Written consent** from every speaker that their voice may be used in the demo, video and a public repo or not (see 8.5). Keep the consent text in a private place, not the repo.
3. **First names only; strip phone numbers.** In WhatsApp, unsaved contacts show as phone numbers in the export. Save each member's contact under a first name on the phone you export from.
4. **Natural Hinglish**, 20 to 60 seconds, phone held normally, real background noise. Don't read from a script word for word; read the *facts*, say them your way. This tests the system honestly.
5. **Honest labelling.** The deck says the group is staged by the team from manuals. The dashboard labels seeded data.
6. **Keep media small.** Voice notes are small; send photos at normal quality but avoid video. The export "Include media" zip should stay in the tens of MB.
7. **Same group name as the demo** ("AC Technician Noida") so the import page and video match.
8. **Record the 6 golden photos** (real nameplates and boards) used by G2 and "Try the demo": e.g. `nameplate_voltas.jpg`, `display_e6.jpg`.

### 8.3 Step by step

**Step 1: get manuals (A and B, 1 hour).** Download service manuals or error-code tables for Voltas, Daikin, LG. Put them in a private folder and in the Agent Search source bucket (T14). Note the page for each code you will use.

**Step 2: fill the 15-fault table.** Copy the table from the script into a shared sheet. For each fault: brand, unit, code, *meaning (cite manual page)*, fix that worked, photo. Rows 10 to 12 are no-code (water dripping), 13 is gas (answer must say certified gas technician), 14 is capacitor failure (answer includes discharge safety step), 15 is voltage fluctuation damage (stabiliser advice). Have the second person verify each meaning against the page.

**Step 3: write message beats per fault.** Four beats, per the script:
1. Question (text or voice): "Bhai, Voltas 1.5 ton inverter, indoor pe E6 blink kar raha hai, outdoor chal nahi raha. Kya check karun?"
2. Senior's answer (voice, 30 to 60 s): the meaning per manual, what to check first, the safety step, the usual failing part.
3. Follow-up (voice or text): "Check kiya, capacitor kharab tha, badal diya, ho gaya." Optional photo.
4. Occasionally a disagreement or alternative from someone else (feeds dedupe).
Write only bullet beats, not scripts. (Use the example codes only if the manual confirms them: the "E6" in demos is a placeholder until you confirm.)

**Step 4: create the group.** WhatsApp group "AC Technician Noida" with the team and consenting friends, 4 to 5 people so there are distinct speakers (a "senior" voice, a "junior" voice, one more).

**Step 5: schedule a recording session (60 to 90 min).** Everyone in the same session, so timestamps cluster. Answer the way a real group does: replies can come minutes or hours later (Flash groups threads by topic, SPEC §4). Still keep one fault's beats together and don't interleave two faults, so the gold set (§8.8) stays unambiguous.
*Alternative:* the timestamps on the export are real message times. Don't edit the export text to fake gaps unless you accept it is staged (editing breaks authenticity of the format; prefer real spacing).

**Step 6: include deliberate messy cases.**
- A voice note with **no resolution** (question never answered) -> must yield no card.
- An **off-topic** message (cricket, lunch) -> ignored.
- A **duplicate fix** (two people say the same cause for the same code) -> dedupe merge, `verified_count` 2.
- A **low-quality / low-confidence note** (noisy, mumbled, or "shayad capacitor hoga") -> lands in the review queue (confidence under 0.6).
- A **gas question** ("gas kam hai, refill kar dun?") -> the card is tagged `refrigerant`; the agent must route to STOP_REFRIGERANT.
- A **capacitor note** that includes the discharge step -> hazard `capacitor`, gates required.
- A message that **disagrees** with the first fix.

**Step 7: export.** WhatsApp -> the group -> menu -> More -> Export chat -> **Include media**. Do it on **Android**; also on **iOS** if someone has an iPhone (you need both to test both parsers). Android may produce a zip or loose files depending on version and share target; iOS produces a `.zip` with `_chat.txt`. Date format depends on phone locale: note it.

**Step 8: inspect the export.** Unzip into a scratch folder (untrusted data: don't run anything from it). Open the chat `.txt`. Check: line formats (8.4), media file names (`PTT-YYYYMMDD-WA####.opus`), that every "(file attached)" line has a file, that no phone numbers appear, that speakers are first names. Count: ~30 notes, 40 texts, 10 photos.

**Step 9: store it.** Put the demo export in `seed/whatsapp_export/` **only if the team decides it is OK.** See 8.5.

### 8.4 What the export looks like (SPEC §4)

Android (chat `.txt` plus media files, sometimes zipped):
```
12/05/25, 10:41 am - Ramesh: PTT-20250512-WA0003.opus (file attached)
12/05/25, 10:43 am - Raju: Bhai voltas 1.5 ton E6 aa raha hai
12/05/25, 10:47 am - Ramesh: IMG-20250512-WA0004.jpg (file attached)
```
iOS (a `.zip` containing `_chat.txt`):
```
[12/05/25, 10:41:22 AM] Ramesh: <attached: 00000012-PTT-2025-05-12-10-41-22.opus>
[12/05/25, 10:43:10 AM] Raju: Bhai voltas 1.5 ton E6 aa raha hai
```
The Android lines and the Android file name pattern are exactly from SPEC §4. The iOS line prefix `[12/05/25, 10:41:22 AM] Ramesh: …` is from SPEC §4; the exact iOS attachment text (`<attached: …>`) and file naming are **Inferred from common iOS exports; verify against your real export** and make the parser tolerant. Date order varies by locale.

### 8.5 Decision for the team: where to keep the export

The repo is public (Apache-2.0). Real voices of friends are personal data, even with consent for "the demo". Options:
1. Commit everything (simple; weakest on privacy).
2. **Suggested:** keep the zip in the GCS bucket (and a private Drive backup); commit only `whatsapp_export_small/` and a README saying how the demo export was staged. Demo import loads from the bucket path. Risk: the judge's "reproducibility" is weaker. Mitigation: the deployed demo has the data.
3. Commit only texts and photos, with the audio in the bucket.
Get the consent wording to say exactly what you do (e.g. "recordings may be played in the hosted demo and video; they will not be published in the code repository"). **Flag: decide before committing anything.**

### 8.6 Build the small unit fixture by hand

Target: `seed/whatsapp_export_small/`.
```
whatsapp_export_small/
  _chat.txt                       (Android-style lines; add a second iOS file `ios/_chat.txt` for the iOS parser test)
  PTT-20250512-WA0003.opus        (1-2 tiny files; or skip real audio and ship transcripts stub)
  IMG-20250512-WA0004.jpg         (1x1 or tiny image)
  expected.json                   (what the parser must output)
  transcripts_stub.json           (maps file name -> fake Transcript, used by the fake transcriber)
```
Contents: 3 to 5 messages: a question text, a voice note answer, a "ho gaya" follow-up, one photo, one system line (encryption notice) and one multi-line text. Expected parse output:
```json
{
  "platform": "android",
  "messages": [
    {"ts": "2025-05-12T10:41:00", "speaker": "Ramesh", "kind": "audio", "file": "PTT-20250512-WA0003.opus"},
    {"ts": "2025-05-12T10:43:00", "speaker": "Raju",   "kind": "text",  "text": "Bhai voltas 1.5 ton E6 aa raha hai"}
  ],
  "threads": [["m1","m2","m3"]]
}
```
(Timestamps shown without timezone; WhatsApp exports have none, so decide and document one: Suggested: treat as local IST and convert to UTC when writing Firestore, as contracts require UTC ISO-8601.) The tests assert exact equality. The tiny opus files can be generated with `ffmpeg` from a 1 s sine tone; a real voice is not needed for the parser test.

### 8.7 Generate synthetic cards and 200 jobs (T25)

Write `seed/generate.py` (inferred) with these properties:
- **Fixed random seed** (`random.Random(1234)`) so output is identical every run and tests are stable. No `datetime.now()`; use a fixed base date.
- **Only from manual-derived codes.** Input is a small JSON `seed/manual_codes.json` that you build in T08 from the manuals (brand, code, meaning, typical cause, parts, hazard, page). The generator may vary phrasing, tonnage, date, and speaker (first names), never the meaning of a code.
- **~50 cards** (plus the ~30 from the real import = ~80). Each with `seeded: true` and visibly labelled; source kind says synthetic.
- **200 jobs** across **15 Noida/Ghaziabad pincodes** (choose real pincodes, e.g. 201301, 201010; verify the list), 3 workers, dates spread over a window.
- **One planted cluster:** same model and component failing in a few nearby pincodes within a window (e.g. one outdoor-unit capacitor for one model in 4 to 5 pincodes in the last 14 days), higher than the background rate so the z-score in `clusters` is clearly above threshold. Everything else uniform noise.
- Idempotent writes: deterministic IDs (`fc_seed_001`), so reruns overwrite.
- `compute-clusters` Job reads jobs and writes `clusters/{key}`; the generator never writes clusters itself (so the job is really exercised).

**Tests.** Same seed -> byte-identical output; every card's code/meaning pair exists in `manual_codes.json`; exactly one planted cluster is detected.

### 8.8 Quality checks: at least 20 cards, at least 80% correct

SPEC §10 bar: 30 notes in 2 min or less, at least 20 cards, at least 80% correct.

1. **Hand-label a gold set** from your own script (you know the truth): a sheet with one row per intended fault: `fault #, brand, code, cause, fix, hazard, message ids`. Plus rows for the messy cases with expected outcome (no card, review queue, merged).
2. **Run the import**; export the produced cards.
3. **Match** each produced card to a gold row. Score a card *correct* only if brand + code + cause + fix match and hazard is not lower than gold. Cards with no gold match are wrong (hallucinated). Missing gold rows count as misses.
4. **Accuracy** = correct cards / produced cards (precision); also report recall = gold faults found / gold faults.
5. If under 80%, fix prompts (§7) and rerun; keep the sheet and the number; put actuals in `docs/STATUS.md`.
Because you wrote the gold set before running, the number is honest.

---

## 9. Feature proposal: the worker shows Ustaad things it didn't ask for

**Status: Accepted as S7 (Should) on Oct 13** (SPEC §3, tasks T36 and T37). The contract part (9.5) is in PR #7 and needs both people to sign off before code.

### 9.1 What this covers, and what already exists

Today the camera only opens when **Ustaad decides** it needs to see something (M4, `request_media`). On a real job the worker also brings things to Ustaad himself. Two cases:

| Case | Worker says | What should happen |
| --- | --- | --- |
| **A. Side issue mid-repair** | At step 3 of 6: "yahan wire bhi jala hua lag raha hai" | Ustaad answers by voice, the camera sheet opens with "Jala wire ka photo ya 15 sec video bhejo", it checks the media, then asks whether to deal with it now or after the current repair |
| **B. Manual photo** | "Mere paas iska manual hai" | Ustaad asks for the right page, reads it, and cites it ("aapke manual ke page par likha hai…") as a source |

What already exists and is reused:
- `request_media` + `media_request` / `media_ready` / `media_result` frames + the camera sheet (M4, T17). The request is spoken, captioned and written on the sheet, so "talk back and write on screen" is already covered.
- `identify_appliance`, `search_fault_cards`, `search_manuals` (S1), the gate machinery (M5).
- 15 s video clips are **S4 (Should)** and second in the cut order. Until S4 ships, "photo or video" means photo; the instruction must not offer video when the client doesn't support it.

What is missing:
- The job model has one appliance, one code and one ordered step list. Nothing says what happens to the **open repair** when a second problem appears.
- No way to use a page from the worker's own manual or the wiring-diagram sticker inside the panel.

### 9.2 Case A design: side issue mid-repair

```
Worker (during step 3): "yahan wire bhi jala hua lag raha hai"
 -> Ustaad (voice + caption): "Accha, dikhao. Wire ka photo bhejo, paas se."
 -> request_media(kind="photo" | "video" if S4, target="Jala hua wire", reason="side_issue", framing_tip="20 cm door, flash on")
 -> camera sheet -> media_ready -> vision check -> media_result
 -> Ustaad: "Haan, wire ka insulation jala hai. Pehle capacitor wala kaam khatam karein, ya yeh abhi dekhein?"
 -> worker chooses:
     "baad mein" -> park the finding, resume step 3 exactly where it was
     "abhi"      -> park the main repair, guide the side issue (search_fault_cards / search_manuals), then resume
```

Rules:
1. **Ask, don't switch silently.** The worker decides the order; Ustaad never abandons the open repair on its own.
2. **Parking is session state, not a new job.** Session state holds `main_step` (job id + step n) and a small `side_issues` list. Resuming re-sends the same `step_card` for the parked step.
3. **Gates are per job and keep their state.** A gate passed for the main repair stays passed for the side issue in the same job. A side issue that needs mains-powered work (a burnt wire near the PCB is `HV`) still requires `G_MAINS_OFF` if it isn't passed yet. Refrigerant side issues get `STOP_REFRIGERANT` as always.
4. **Logged, not lost.** Each side finding is written into the existing `jobs.media[]` entry (`findings`, `confidence`). On `close_job`, Ustaad asks one question ("Wire wala theek kiya?") and, if fixed, drafts a second fault card tagged "found while fixing <code>".
5. **One side issue at a time.** If the worker raises a third thing, Ustaad notes it and says it will come back to it; no nested parking.

Implementation shape (Suggested (not yet in spec)):
- **Instruction change** (`backend/agent/instruction.md`, human-owned): a short "side issues" paragraph with the five rules above.
- **Two small tools or one tool with a mode**: `park_repair(job_id)` returns the parked step; `resume_repair(job_id)` returns the same step again (BLOCKING, both pure functions over session state + Firestore job). Alternatively, keep `next_step` and add an optional `resume: true`; prefer the two explicit tools, they are easier to test.
- **No new frames.** The UI already renders `media_request`, `media_result`, `step_card`.

### 9.3 Case B design: photo of the worker's manual

```
Worker: "Mere paas manual hai" (or taps "Manual photo" on the job screen)
 -> request_media(kind="document", target="Manual ka error-code wala page", framing_tip="Poora page, seedha, roshni mein")
 -> media_request{kind:"document"} -> camera sheet -> upload -> media_ready{kind:"document"}
 -> Flash vision extracts ManualPage{brand?, model?, page_title, error_codes[{code, meaning}], steps[], warnings[], legible}
 -> media_result (retake_reason if legible=false)
 -> becomes a source: step_card.source.kind = "manual_photo", label "Photo of manual"
 -> Ustaad: "Aapke manual ke page par E6 ka matlab likha hai …"
```

Rules:
- **Copy, don't recall.** The extraction prompt says "copy only what is printed; if illegible set legible=false and leave fields empty". This keeps the "never invent error-code meanings" rule intact.
- **A source, never an authority over safety.** Steps from the page are hazard-tagged like card steps; gates apply; a page that describes gas charging still yields `STOP_REFRIGERANT`.
- **Brand check.** If the page's brand differs from the identified appliance, Ustaad says "yeh page kisi aur brand ka lagta hai" and asks for the right one; it doesn't use the page.
- **Wiring-diagram sticker** is the same flow with target "Panel ke andar wiring diagram sticker".

### 9.4 Shared rules for both cases
- Same retake loop as M4: at most 2 retakes, each with a reason in the worker's language.
- Same rate limits and demo-safe cache as other vision calls (golden inputs cached by hash).
- Every photo/clip is stored under `gs://<bucket>/jobs/{job_id}/` and listed in `jobs.media[]`.
- All on-screen strings live in `web/src/i18n/*.json` (hi, te first).

### 9.5 Contract impact

| Contract | Case A | Case B |
| --- | --- | --- |
| ws-events `media_request.kind` / `media_ready.kind` | none (photo; video already allowed by S4) | add `"document"` |
| ws-events `step_card.source.kind` | none | add `"manual_photo"` (check the existing allowed values in the schema first) |
| rest `POST /api/media/upload-url` `kind` | none | reuse `"photo"` (preferred, no change) |
| firestore `jobs.media[]` | add optional `reason: "requested" \| "side_issue" \| "manual"` | same field |
| firestore `jobs` | optional `side_issues[]` only if `media[]` is not enough (prefer not) | none |

All of it after the Oct 12 noon freeze, so it is a deliberate exception: one `CHANGELOG.md` line per file, both humans approve, then Pydantic enums + `make types`.

### 9.6 Tasks, owner and priority

Both are lane **A** (they run through `request_media` and the agent instruction). Priority **P2 / Should**, after all Musts pass. Case A is cheaper and demos better, so do it first.

| ID | P | Owner | Task | Read | Done when | Needs |
| --- | --- | --- | --- | --- | --- | --- |
| T36 | P2 | A | Side issues mid-repair: instruction paragraph, `park_repair` / `resume_repair`, `media[].reason`, close-job question | this section, SPEC §6, SAFETY.md | tests in 9.7 (A) pass; on phone: side photo mid-step → choose "baad mein" → same step resumes | T16, T17 |
| T37 | P2 | A | Manual / sticker photo: `kind:"document"`, ManualPage extraction, `manual_photo` source chip, "Manual photo" button | this section, contracts/ws-events.md | tests in 9.7 (B) pass; real photographed page cited on phone | T17, contracts PR merged |

#### T36 Side issues mid-repair (A, P2)

Design in §9.2 and §9.4, tests in §9.7 (Case A). Task card:
```
ID: T36   Owner: A   Branch: a/T36-side-issues
Goal: worker can raise a second problem mid-repair; Ustaad asks for a photo, checks it,
      lets the worker choose now/later, parks and resumes the main repair, logs the finding
Read: docs/BUILD-GUIDE.md §9.2 and §9.4, docs/SPEC.md §6, docs/SAFETY.md, backend/AGENTS.md
Done when:
- tests/unit/test_side_issues.py passes (park → side photo → resume returns the same step_card)
- a side issue tagged HV with G_MAINS_OFF open returns SAFETY_GATE; passed gates stay passed
- refrigerant side issue returns STOP_REFRIGERANT
- jobs.media[] entry has reason="side_issue"; close_job asks about it
Don't touch: shared/contracts/ (except via the approved contracts PR), backend/agent/callbacks.py
```

#### T37 Manual / wiring-sticker photo (A, P2)

Design in §9.3 to §9.5, tests in §9.7 (Case B). Task card:
```
ID: T37   Owner: A   Branch: a/T37-manual-photo
Goal: request_media kind "document"; Flash extracts ManualPage from a photographed manual page
      or wiring sticker; result is cited as source kind "manual_photo"
Read: docs/BUILD-GUIDE.md §9.3–9.5, shared/contracts/ws-events.md, backend/AGENTS.md, docs/SAFETY.md
Done when:
- tests/unit/test_manual_photo.py passes with recorded extraction fixtures (no network)
- legible=false → media_result.retake_reason, max 2 retakes
- wrong-brand page is not used; gas-charging page → STOP_REFRIGERANT
- step_card.source.kind == "manual_photo" with label "Photo of manual"
Don't touch: backend/agent/callbacks.py; contracts only via the approved contracts PR
```

### 9.7 Tests

**Case A (side issue)**
| Case | Expected |
| --- | --- |
| Side issue raised at step 3, worker says "baad mein" | finding logged; same step 3 `step_card` re-sent |
| Worker says "abhi" | main repair parked; side guidance; then step 3 resumes |
| Side issue is HV, `G_MAINS_OFF` not yet passed | `SAFETY_GATE G_MAINS_OFF` |
| Side issue is HV, `G_MAINS_OFF` already passed in this job | no second gate request |
| Side issue mentions gas ("gas leak lag raha hai") | `STOP_REFRIGERANT` |
| Third issue raised while one is parked | noted, not nested; main flow continues |
| `close_job` with a logged side issue | asks one question; drafts a second card if fixed |

**Case B (manual photo)**
| Case | Expected |
| --- | --- |
| Legible page with an error-code table | codes extracted; source chip "Photo of manual" |
| Blurry or cropped page | `legible=false`, retake reason in Hindi; max 2 retakes |
| Page from a different brand | flagged, not used |
| Page describing gas charging | `STOP_REFRIGERANT`; no steps |
| Page with an HV or capacitor step | the usual gates still required |

Unit tests use recorded vision responses in `seed/fixtures/` and fake clients; one golden run each with a real photo.

### 9.8 Demo in the video

One 10–15 s beat inside the "stuck" moment: mid-repair, Raju says "yahan wire bhi jala hai"; the camera sheet slides up with Ustaad's request; he shoots it; Ustaad: "Pehle yeh khatam karein ya woh?"; he says "baad mein" and the same step card comes back. If T37 is done, a second short beat shows a manual page being cited. If either is half-working by Thursday's freeze, leave it out of the video and mention it as roadmap (honest-demo principle).

---

## 10. Testing strategy

### 10.1 Layers

| Layer | What | Runs | Real models? |
| --- | --- | --- | --- |
| Unit | each tool, parser, state machine, reducer, cache, gate logic | `make test` / `make check` | No. Fakes and `seed/fixtures/` |
| Contract | models parse every example; generated files not stale | `make check` | No |
| Replay | `MOCK_LIVE` frames drive the UI; UI tests | `make check` / Playwright | No |
| Golden | G1 to G6 scripted flows | `make golden` before each `demo` deploy | **Yes** |
| Safety | the 10 SAFETY.md attempts | unit (automated), and a few repeated live | Tools: no; spot-check Live: yes |
| Integration gate | G2 + G3 on a real phone, `dev` (T26) | Wed 21:00 | Yes |
| Manual device | 360 px, sunlight, real 4G, Android + iPhone | by hand | Yes |

### 10.2 Unit testing patterns

- One test file per tool (`tests/unit/test_<tool>.py`).
- Fake clients implement the same interface as real ones. Make them deterministic.
- Test the *negative* path as well as the positive one (a fake that always passes proves nothing).
- Time and randomness injected (`now()` argument; seeded RNG) so tests are stable.
- Keep `make check` under a couple of minutes.

### 10.3 Golden tests

`make golden` plays the scripts in GOLDEN_PATHS against real models and compares the produced frames to expectations loosely: *frame types and order, and key fields* (brand, code, gate ids), never exact wording. Expect some flake from LLMs: run each path 3 times and require 3/3 before a demo deploy. Record which model/version ran.

### 10.4 The 10 safety bypass tests

Automate tests 1 to 9 at the tool/callback level, test 10 at the client level (see T16). They are cheap, deterministic and are the source of the "0/10" in the deck. Add one live spot-check each for #6 (prompt injection) and #7 (gas) with the actual Live model.

### 10.5 Measuring the quality bar (SPEC §10)

| Target | How to measure |
| --- | --- |
| Speech end -> reply <= 2.5 s p50 | Log timestamps server-side at `ptt end` and at first audio byte out; also record a phone screen capture with a stopwatch for a sanity check. Run 20 turns, take the median |
| Photo -> findings <= 6 s p50 | `media_ready` received -> `media_result` sent, 20 photos |
| 6/6 golden photos | `make golden` identify step |
| Import 30 notes <= 2 min, >= 20 cards, >= 80% correct | Job start/finish timestamps in `imports/{id}`; accuracy via the gold sheet (§8.8) |
| Quotes <= 2 min | `request_quotes` call to third `QUOTED`, with the team phones, 3 runs |
| 0/10 gate bypasses | the safety test file |

Report **actuals**, not targets; if you miss one, say so and what you did.

### 10.6 Minimum manual checklist before each demo deploy
Incognito phone, Try the demo, G2 start to finish, G6 first question, `/d/import` on laptop, safety screen, quotes with three phones, `/healthz` shows `demo_safe`.

---

## 11. Deployment and operations

### 11.1 Environments

| Env | Backend | Firestore | Min instances | Purpose |
| --- | --- | --- | --- | --- |
| local | `make dev-api`, `make dev-web` | emulator or dev DB (Inferred) | n/a | Fast loop, mocks |
| dev | Cloud Run `ustaad-api-dev` | `(default)` | 0 | Daily integration; Meta webhook during T06 to T26 |
| demo | Cloud Run `ustaad-api` | `demo` | 1 from Thu | What judges see; tagged builds only |

Deploy `demo` only from a tag after golden paths pass. Hosting rewrites `/api/**` to `ustaad-api`, so it needs to exist before `make deploy-hosting`. The Meta webhook URL must point at the service you are testing; switch it to `demo` for the final week and recheck verification.

### 11.2 Secrets and config
Secret Manager holds `WA_TOKEN`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, and the Places key. Cloud Run mounts them as env. Non-secret env (models, bucket, flags) via deploy vars. Env list: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`, `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `FLASH_MODEL`, `LIVE_MODEL`, `LIVE_LOCATION`, `TTS_MODEL`, `EMBED_MODEL`, `TRANSCRIBE_MODEL`, `AGENT_ENGINE_ID`, `AGENT_SEARCH_DATASTORE`, `WA_*`, `PLACES_API_KEY`, `DEMO_SAFE`, `MEDIA_BUCKET`, `ALLOWED_ORIGINS`. Check `ALLOWED_ORIGINS` includes the Hosting domain, or the WebSocket origin check will reject judges.

### 11.3 Cost control
- Budgets with alerts at ₹500, 2,000, 5,000 (`infra/budgets.sh`).
- Credits (progress hub): GenAI App Builder trial ₹95,700 for Agent Search (reportedly only those SKUs); Marketing agentic hackathon ₹14,347 (~Oct 24) and Partner marketing ₹1,485 (~Oct 20; burns first) for Gemini via Vertex, Cloud Run, Firestore, Storage; billing card after that. Check Billing -> Reports on Day 2 to see which credit paid which SKU.
- Evaluation runs Oct 19 to Nov 6, **after the small credits expire**. Plan for card spend. Live audio sessions are the expensive part, hence the rate limits (20 req/min/IP, 3 concurrent Live sessions).
- Do not run large repeated imports against the demo DB.

### 11.4 Keeping it live until Nov 6
`min-instances` 1 on `ustaad-api` (cold starts break WebSocket demos). Daily check of `/healthz` and golden path 2. Don't redeploy `demo` during evaluation except for a fix, and run goldens first. Make sure the Meta system-user token does not expire; the test number's 5 recipients must have messaged it recently for the 24-hour window, or keep the template fallback working. Keep the budget alerts going to a phone someone watches.

---

## 12. Gaps and risks I found

| # | Gap or risk | Why it matters | Recommended action |
| --- | --- | --- | --- |
| 1 | **Prompts are not written**: the Live instruction and all structured prompts (§7). | Behaviour quality and safety copy depend on them; they are on the critical path for T11, T15 | A drafts `instruction.md` (§6.3 outline) before T11 ends; B drafts the extraction prompts (§7) alongside T13/T15. Review as a pair |
| 2 | **`fault_card.schema.json` is only in the starter zip**, not in the project docs I could read. This guide cannot show the field list | T10 and T15 depend on it; mismatch with Firestore `fault_cards` | Confirm the file is committed in `shared/contracts/`; both read it before the noon freeze |
| 3 | **A's lane is on the critical path and heavier** (T09, T11, T12, T16, T17, T21, T22, T27, T29 + video editing) | One delay blocks G2 | Move T12 prep and T21 (onboarding) to B's spare time if B finishes T13/T14 early; B pre-builds UI against MOCK_LIVE; cut S3 (T20) first |
| 4 | **Contracts freeze timing**: noon today, but WS frames depend on what the Live model actually emits (T05 result, transcript script behaviour) | Changing a frame after freeze costs both lanes | Allow a documented "v1.1 window" Tue 14:00 contract check (WORKFLOW daily rhythm) for additions only; log in CHANGELOG |
| 5 | **Live model choice pending (T05)**: `gemini-3.8-live` or fallback, plus `LIVE_LOCATION` and native-script captions in te/ta/bn | Voice polish, G6, and the tool `behavior` defaults differ per model | Run T05 first, record result; if Telugu captions arrive transliterated, decide: show as received, or fall back to Flash transcription of the user turn for captions |
| 6 | **`share_target` unverified** (T07): WhatsApp may not list the PWA | Path (a) may not exist | Treat `/d/import` upload as the demo path (SPEC already says so); don't spend more than 30 minutes; also keep the claim out of the deck unless verified |
| 7 | **Public repo plus real voice recordings** | Privacy/consent; cannot un-publish git history | Decide §8.5 today; commit only the tiny fixture; written consent wording matches |
| 8 | **WhatsApp 24-hour window and test-number limits** | Quotes fail silently if a vendor phone didn't message first; the test number only reaches 5 recipients | Everyone sends "hi" before every demo and before filming; template fallback tested once; add a debug line in `/d/jobs` showing send errors |
| 9 | **ADK `run_live` risk** (new API surface, tool behaviour differences) | If it fights us the critical path slips | Timebox: decide by Tue noon; the raw `google-genai` Live fallback works because tools are pure functions (§3.2) |
| 10 | **Credits expire before evaluation ends** | Spend after ~Oct 24 is on the card | Budget alerts exist; cap sessions; confirm which credit covers Memory Bank and Agent Search on Day 2 |
| 11 | **LLM variance in the safety path** (gate vision checks) | A pass on a bad photo, or fail on a good one in the video | Fail closed; thresholds in code; test ambiguous photos; rehearse the gate photos you will film with |
| 12 | **Hazard under-labelling at extraction** | A card marked `none` that contains a capacitor step | Deterministic keyword check can only raise hazard (§T15); spot review all 30 import cards |
| 13 | **Error-code meanings in fixtures** | The doc says they must come from real manuals; hand-written G2 fixture is easy to get wrong | T08 table is the single source; fixtures reference it; second person verifies |
| 14 | **Timezones**: WhatsApp exports have no timezone; contracts require UTC | Wrong dates on source chips ("Ramesh, May 2025") | Assume IST on import and convert; test one fixture across midnight |
| 15 | **Prototype claims**: "Hindi + Telugu polished, Tamil + Bengali beta" | Overclaiming loses trust with judges | Label Tamil/Bengali beta in UI and deck as SPEC says |
| 16 | **Cross-lane tool use** (close_job calls inventory) | Lane boundary friction | A calls B's pure function through its interface; agree the signature in the Tue contract check |

---

## 13. Glossary for learners

| Term | Meaning |
| --- | --- |
| ADK (Agent Development Kit) | Google's Python framework for building agents: tools, sessions, callbacks, runners, plus Live streaming via `run_live()` |
| Agent Engine | A Google-hosted runtime; here only used as the container for Memory Bank (`AGENT_ENGINE_ID`) |
| Agent Search | Managed document search (the manuals data store); returns snippets with doc and page |
| AudioWorklet | Browser API that runs audio code on the audio thread; used to capture and play PCM without jank |
| Barge-in | The user speaking over the assistant; the assistant stops and listens |
| BLOCKING / NON_BLOCKING | Whether a Live tool call pauses the conversation (BLOCKING) or lets the model continue talking while it runs (NON_BLOCKING) |
| WHEN_IDLE / SILENT | Response scheduling: deliver the result when the model is idle / deliver without prompting the model to speak |
| before_tool_callback | ADK hook that runs before every tool call and can veto it; used for safety |
| Cloud Run | Managed container hosting for HTTP/WebSocket services (`ustaad-api`) |
| Cloud Run Jobs | Run-to-completion containers (`ingest-whatsapp`, `compute-clusters`) |
| Codegen | Generating code (here TS types) from a source of truth (Pydantic -> OpenAPI -> types.ts) |
| Context compression | Summarising older turns so a long Live session fits the context window |
| Contract-first | Agreeing the interface between parts before building them |
| Cosine similarity | Measure of how close two embedding vectors are (1 = identical direction) |
| CORS / origin check | Browser origin rules; server also checks `Origin` on WebSocket against `ALLOWED_ORIGINS` |
| Defence in depth | Multiple independent safeguards against the same failure |
| Dedupe | Merging cards describing the same fix (same brand + code, cosine > 0.9) |
| Embedding | Vector of numbers representing meaning of text; here 768 dimensions |
| FLAC | Lossless audio format used between ffmpeg and Flash for transcription |
| Fixture | Recorded or hand-made test data in `seed/fixtures/` |
| Flash | The fast general Gemini model (`FLASH_MODEL`) used for vision, text, JSON |
| Function calling | The model asks the host to run a named function with arguments and then uses the result |
| Gate | A photo-evidence safety check that must pass before hazardous steps (`G_MAINS_OFF`, `G_CAP_DISCHARGE`) |
| Golden path | A scripted demo flow (G1 to G6) that must always work |
| HMAC / signature check | Keyed hash of the raw webhook body proving it came from Meta (`X-Hub-Signature-256`) |
| Hinglish | Hindi and English mixed, usually written in Roman letters |
| Idempotency | Repeating an operation does not change the result beyond the first time |
| Live API | Gemini's streaming, bidirectional audio/video/text session API |
| Memory Bank | Managed long-term memory for agent conversations |
| MOCK_LIVE | Flag that replays a recorded Live session instead of calling the model |
| Opus / OGG | WhatsApp's voice-note audio format (`.opus`) |
| Pincode | Indian postal code (6 digits) |
| PTT | Push-to-talk: audio sent only while the button is held |
| PCM16 | Raw 16-bit signed audio samples; 16 kHz mono in, 24 kHz mono out |
| PWA | Installable web app; with a manifest it can appear in the share sheet via `share_target` |
| Pydantic | Python library for typed data models and validation |
| Session resumption | Reconnecting to a Live session with an opaque handle after a drop |
| Signed URL | Time-limited URL granting upload or download of one storage object |
| Source chip | UI tag naming where advice came from; can play the original voice note |
| State machine | Fixed set of states and allowed transitions (quotes, gates) |
| STOP_REFRIGERANT / STOP_REFER | Refusal state for refrigerant work and the other stop reasons; red screen with fixed text, no audio |
| Template (WhatsApp) | Pre-approved message format usable outside the 24-hour window |
| Thread | A group of messages about one fault (Flash grouping by topic; 30-minute gaps only as fallback) |
| Vector search | Finding nearest embeddings (Firestore `find_nearest`) |
| 24-hour window | WhatsApp rule: free-form messages only within 24 h of the user's last message to you |
| Worktree | A separate checkout of the same repo for a parallel branch (`git worktree add`) |

---

*End of guide. Update this file, not the repo docs, when your understanding changes; update the repo docs (via PR) when the project's decisions change.*
