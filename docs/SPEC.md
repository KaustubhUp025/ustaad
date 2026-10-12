# Ustaad — Ground Truth Spec (repo copy)

This repo file is authoritative. The shared "Ustaad — Ground Truth Spec" doc mirrors it for humans; change this
file first (PR), then the doc. Aim and judging: `docs/PRODUCT.md`. Tasks: `docs/TASKS.md`. Safety: `docs/SAFETY.md`.
Submission: **Sat Oct 17, 2026, 21:00 IST**. Feature freeze: **Thu Oct 15, 18:00**.

## 1. Locked decisions

| Area | Decision |
| --- | --- |
| Product | Voice-first assistant for Indian AC and appliance repair technicians. Other trades: roadmap. |
| Theme | Future of Work & Enterprise Productivity |
| Languages | Hindi + Telugu polished (in the video); Tamil + Bengali work, labelled beta; English UI for judges |
| Surfaces | One Vite + React PWA: worker app `/w`, team dashboard `/d`. No native app. |
| Backend | One FastAPI service on Cloud Run (asia-south1): ADK agent, REST, Live WebSocket, WhatsApp webhook. Batch = Cloud Run Jobs. |
| Models | Vertex / Agent Platform only. `FLASH_MODEL=gemini-3.8-flash`. `LIVE_MODEL=gemini-3.8-live` if the Day-1 smoke test passes on Agent Platform, else `gemini-live-2.5-flash-native-audio`. |
| Transcription | ffmpeg → 16 kHz mono FLAC → Flash `generateContent` (MIME `audio/flac`). `gemini-3.5-transcribe` optional (preview, Interactions API). |
| Knowledge | Fault cards in Firestore, 768-dim vectors (`gemini-embedding-001` with `output_dimensionality=768`; default is 3072). Manuals in Agent Search (₹95.7k credit). |
| Memory | Memory Bank via an empty Agent Engine instance (`AGENT_ENGINE_ID`); Firestore for structured data |
| Camera | Snapshots and ≤15 s clips requested by the agent. No continuous video stream. |
| Vendors | WhatsApp Cloud API test number, 5 registered team phones as vendors |
| Payments | None (at most a `upi://` link) |
| Repo | Public GitHub, Apache-2.0, English docs, created Oct 11 |
| Ops | Services stay live through Nov 6 (evaluation Oct 19 – Nov 6) |

## 2. Hackathon requirements (all are release blockers)

Deployed link (Cloud Run / Firebase) · Gemini or Gemma models · public GitHub repo · fresh project built in the
hackathon window · video under 3 minutes (public YouTube/Vimeo/Drive) · deck PDF · all materials in English ·
theme named. Rules don't mention AI coding assistants. Source: https://aibuildercup.com/Faqs.html

## 3. Scope

### Must
| ID | Feature | Acceptance test (real Android phone, deployed build) |
| --- | --- | --- |
| M1 | Voice onboarding | Language pick + 6 spoken questions; profile card fills live; saved. Hindi and Telugu. |
| M2 | Stuck mode: identify + guide | Golden nameplate + error photo → correct brand/model/code; spoken fix with source chip that plays the original note |
| M3 | Talk-back with captions | Every reply heard and shown as live captions in the worker's script; his words as a bubble; step card stays |
| M4 | Agent asks to see | Mid-repair photo request with framing tip; checked; continue or one retake with a reason |
| M5 | Safety gates | Hazardous step hidden until a photo passes; refrigerant → "certified gas technician needed"; skip attempts fail |
| M6 | WhatsApp import | Demo export (zip or loose files) → ≥20 fault cards with speaker, date, audio link, arriving live on the dashboard |
| M7 | Stock | "Do capacitor use kiye" decrements; repair checks stock first; low-stock badge |
| M8 | Parts quotes | Missing part → 3 vendor phones on WhatsApp → text/voice replies parsed and ranked → approve sends confirmations; < 2 min |
| M9 | Close job | "Ho gaya" → job log + new fault card with photo; stock updated |
| M10 | Judge-ready demo | "Try the demo": seeded worker, sample photos, cached golden paths; works in incognito on phone and laptop |

### Should (only after all Musts pass)
S1 manuals via Agent Search with page citations · S2 area cluster map (seeded, badged) · S3 Memory Bank coaching
nudges · S4 15 s video clips · S5 Tamil/Bengali polish · S6 pre-job brief

### Won't
Payments, native app, real auth, multi-team tenancy, other trades, continuous camera streaming, Gemma on-device,
reading WhatsApp groups directly.

### Cut order if behind
Live-look streaming → 15 s clips → Tamil/Bengali depth → shelf-photo counting → nudges as rules → map as table.
Never cut: M2–M5 (spoken + captioned guidance, agent-requested photos, safety gate), M6 import, M8 quotes.

## 4. WhatsApp knowledge import
No API reads groups. Use WhatsApp "Export chat → Include media".
- Paths: (a) share the export to the installed PWA (`share_target`; unverified that WhatsApp lists PWAs),
  (b) upload zip or loose files at `/d/import` (the demo path), (c) forward one voice note to the WhatsApp number (Should).
- Android: chat `.txt` + media, sometimes zipped. Voice notes `PTT-YYYYMMDD-WA####.opus`; line
  `12/05/25, 10:41 am - Ramesh: PTT-20250512-WA0003.opus (file attached)`.
- iOS: `.zip` with `_chat.txt`; lines `[12/05/25, 10:41:22 AM] Ramesh: …`. Date order varies by locale.
- Pipeline (Cloud Run Job `ingest-whatsapp`): upload to `gs://<bucket>/imports/{id}/` → parse messages → audio:
  `ffmpeg -i x.opus -ac 1 -ar 16000 x.flac` → Flash transcript `{text, language, confidence}` (keep Hinglish,
  codes and part numbers verbatim) → photos described → threads (30-min gaps + Flash grouping) → one card per
  resolved thread with sources → dedupe (same brand+code and cosine > 0.9 → merge, `verified_count++`) → embed →
  write; confidence < 0.6 → review queue. Progress in `imports/{id}`. Target: 30 notes < 2 min, 8 parallel.
- Consent: only groups whose members agree. Strip phone numbers.

## 5. Architecture
PWA (Firebase Hosting, `/api/**` rewritten to Cloud Run) · Live voice opens `wss://` **directly** to the Cloud Run
URL (Hosting rewrites don't carry WebSockets; `--timeout=3600`, session affinity, origin check) · `ustaad-api`
(FastAPI + ADK) · Jobs `ingest-whatsapp`, `compute-clusters` · Agent Platform (Live, Flash, TTS, embeddings,
Memory Bank) · Agent Search (manuals) · Firestore + Storage · Places API (New) · WhatsApp Cloud API.

Credits: ₹95.7k GenAI App Builder → Agent Search only (reportedly). ₹14.3k (≈Oct 24) and ₹1.5k (≈Oct 20) →
Gemini, Cloud Run, Firestore, Storage, Memory Bank. Card + alerts (₹500/2,000/5,000) after that.
Rate limits: 20 req/min per IP on `/api/chat` and `/ws/live`, 3 concurrent Live sessions.

Env: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`,
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `FLASH_MODEL`, `LIVE_MODEL`, `LIVE_LOCATION` (region for the Live client; the smoke test uses the same value), `TTS_MODEL=gemini-3.8-flash-tts`,
`EMBED_MODEL=gemini-embedding-001`, `TRANSCRIBE_MODEL` (empty = Flash), `AGENT_ENGINE_ID`,
`AGENT_SEARCH_DATASTORE`, `WA_TOKEN`, `WA_PHONE_ID`, `WA_VERIFY_TOKEN`, `WA_APP_SECRET`, `PLACES_API_KEY`,
`DEMO_SAFE`, `MEDIA_BUCKET`, `ALLOWED_ORIGINS`.

## 6. Agent
`build_ustaad(model)` → one ADK agent; Live via `runner.run_live()`, text via `runner.run_async()`; same tools.
Tools are framework-free functions in `backend/tools/` (fallback: raw `google-genai` Live client calls them).

| Tool | Input | Output | Live `behavior` / response scheduling |
| --- | --- | --- | --- |
| save_profile_fields | partial profile | profile | NON_BLOCKING, SILENT |
| identify_appliance | media_uri | brand, model, series, type, error_code, confidence | BLOCKING |
| request_media | kind photo/video, target, reason, framing_tip | media_uri, findings, matches_expected, confidence, follow_up | NON_BLOCKING, WHEN_IDLE |
| search_fault_cards | brand, model?, error_code?, symptom? | top 5 with citation {author, date, audio_uri} | BLOCKING |
| search_manuals | query, brand, model? | snippets {text, doc, page} | BLOCKING |
| start_repair | job_id, card_ids | steps {n, instruction, hazard none/HV/capacitor/refrigerant, source} | BLOCKING |
| next_step | job_id, observation, media_uri? | next step or SAFETY_GATE{gate_id, required_evidence} | BLOCKING |
| confirm_safety | job_id, gate_id, media_uri | passed, reason | BLOCKING |
| check_inventory / update_inventory | part / [{part, delta}] | stock + low flags | BLOCKING / SILENT |
| find_vendors | part, pincode | saved + Places results | BLOCKING |
| request_quotes | job_id, part, specs, vendor_ids | quote_request_id | NON_BLOCKING |
| get_quotes / approve_quote | ids | ranked quotes / confirmation | BLOCKING |
| close_job | job_id, outcome, parts_used, fix_summary | job log + draft card id | BLOCKING |
| get_nudges / get_area_alerts | worker_id / pincode | nudges / clusters | BLOCKING |

Set `behavior` explicitly on every function declaration (defaults differ between Live models). Scheduling
(WHEN_IDLE, SILENT) is set on the function response, not the declaration. Safety gates and copy: `docs/SAFETY.md`.
Instruction: patient senior technician; worker's language, Hinglish fine; one instruction at a time; ground fixes
in cards/manuals and say the source aloud; ask to see instead of guessing; never describe a hazardous step before
its gate; never give refrigerant steps or bypass safety devices; check stock before suggesting parts; end with close_job.
Safety in code: `next_step` returns SAFETY_GATE while a gate is open; `before_tool_callback` blocks next_step and
close_job with open gates; refrigerant → STOP_REFER; client shows a red screen + stored warning audio.
Live: AUDIO modality, input + output transcription on, language from profile, session resumption, context
compression, PCM16 16 kHz in / 24 kHz out, push-to-talk.
Memory: Memory Bank (soft facts, end of session; PreloadMemoryTool) · Firestore (structured) · session state (job, step, gates).

## 7. Contracts (frozen Mon Oct 12, 12:00)
Firestore: `workers/{wid}` (+ `inventory`, `vendors`), `jobs`, `fault_cards`, `imports`, `quote_requests`, `quotes`,
`clusters`, `wa_messages` (dedupe), `demo_cache`. Field lists: `shared/contracts/firestore.md`. Fault card schema: `shared/contracts/fault_card.schema.json`.
REST request/response shapes: `shared/contracts/rest.md`. Changes: `shared/contracts/CHANGELOG.md`.
Vector index: `infra/firestore.sh`.
REST: `POST /api/demo/session` · `POST /api/chat` · `POST /api/media/upload-url` · `GET/POST /api/jobs`,
`GET /api/jobs/{id}` · `GET /api/fault-cards`, `GET/PATCH /api/fault-cards/{id}` · `GET/PATCH /api/inventory` ·
`GET/POST /api/vendors` · `POST /api/quotes/request`, `GET /api/quotes/{qrid}`, `POST /api/quotes/{qid}/approve` ·
`POST /api/imports`, `GET /api/imports/{id}` · `GET /api/clusters`, `/api/nudges`, `/api/dashboard/summary` ·
`GET/POST /webhook/whatsapp` · `GET /healthz`.
WebSocket events: `shared/contracts/ws-events.md`.
Quotes per vendor: CREATED → SENT → PARSING → QUOTED → CONFIRMED; CLARIFY (one follow-up); EXPIRED (30 min);
DECLINED. Vendor phones send "hi" before demos (24-hour window); `hello_world` template fallback.

## 8. Frontend
See `docs/DESIGN.md` (tokens, type, layout, words). Routes: `/w/start`, `/w/onboard`, `/w`, `/w/job/:id`,
`/w/stock`, `/w/me`, `/d/knowledge`, `/d/import`, `/d/area`, `/d/jobs`.
Share target accepts `.zip, application/zip, .opus, audio/ogg, audio/opus, text/plain, image/*`; files go to
IndexedDB, then chunked upload; manual picker always available.
Mic: AudioWorklet → 16 kHz PCM16, 40 ms chunks while held; playback worklet 24 kHz; barge-in stops playback.
Camera: `<input type="file" accept="image/*" capture="environment">`; resize to 1600 px JPEG.
i18n: `web/src/i18n/{en,hi,te,ta,bn}.json`.

## 9. Conventions
Branches `a/<ID>-slug`, `b/<ID>-slug`; commit prefix = feature ID; contracts PRs reviewed by the other person;
CI must pass; golden paths before each `demo` deploy; prompts are versioned files; secrets only in Secret Manager;
Python 3.12 + uv + ruff; Node 22 + pnpm. Envs: local, `dev` (Cloud Run `ustaad-api-dev`, min 0), `demo`
(`ustaad-api`, min 1 from Thu, Firestore database `demo`).

## 10. Demo data and quality bar
Seed: WhatsApp group export (~30 real Hinglish voice notes, ~40 texts, ~10 photos) · ~80 cards (~50 synthetic,
labelled) · 3 brands' manuals · 200 jobs in 15 Noida/Ghaziabad pincodes with one planted cluster · 3 workers ·
6 golden photos. Error-code meanings must come from the real manuals, not from memory.
Golden paths (exact inputs and expected frames): `docs/GOLDEN_PATHS.md`.
Demo-safe: cache golden-path responses by input hash; fall back after 6 s; min-instances 1; vendor "hi" first.
Targets (measure, report actuals): speech end → reply ≤ 2.5 s p50 · photo → findings ≤ 6 s p50 · 6/6 golden
photos · import 30 notes ≤ 2 min, ≥ 20 cards, ≥ 80% correct · quotes ≤ 2 min · 0/10 gate bypasses.
