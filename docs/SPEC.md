# Ustaad — Ground Truth Spec (repo copy)

This repo file is authoritative. The shared "Ustaad — Ground Truth Spec" doc mirrors it for humans; change this
file first (PR), then the doc. Aim and judging: `docs/PRODUCT.md`. Tasks: `docs/TASKS.md`. Safety: `docs/SAFETY.md`.
Submission: **Sat Oct 17, 2026, 21:00 IST**. Feature freeze: **Thu Oct 15, 18:00**.

## 1. Locked decisions

| Area | Decision |
| --- | --- |
| Product | Voice-first assistant for Indian AC and appliance repair technicians. AC is the deep path (fault cards and manuals). Fridge, washing machine, LED TV, microwave, geyser and fan/cooler get clearly labelled general guidance through the same tools and gates (§6 source tiers). Other trades: roadmap. |
| Theme | Future of Work & Enterprise Productivity |
| Languages | Hindi + Telugu polished (in the video); Tamil + Bengali work, labelled beta; English as a fifth profile language (spoken and UI) |
| Surfaces | One Vite + React PWA: worker app `/w`, team dashboard `/d`. No native app. |
| Backend | One FastAPI service on Cloud Run (asia-south1): ADK agent, REST, Live WebSocket, Telegram vendor webhook. Batch = Cloud Run Jobs. |
| Models | Vertex / Agent Platform only. `FLASH_MODEL=gemini-3.8-flash`. `LIVE_MODEL=gemini-3.8-live` if the Day-1 smoke test passes on Agent Platform, else `gemini-live-2.5-flash-native-audio`. |
| Transcription | ffmpeg → 16 kHz mono FLAC → Flash `generateContent` (MIME `audio/flac`). `gemini-3.5-transcribe` optional (preview, Interactions API). |
| Knowledge | Fault cards in Firestore, 768-dim vectors (`gemini-embedding-001` with `output_dimensionality=768`; default is 3072). Manuals in Agent Search (₹95.7k credit). |
| Memory | Memory Bank via an empty Agent Engine instance (`AGENT_ENGINE_ID`); Firestore for structured data |
| Camera | Snapshots and ≤15 s clips requested by the agent. No continuous video stream. |
| Vendors | A Telegram bot; team phones that pressed Start on it are the saved vendors (WhatsApp Cloud API blocked by Meta business verification, DECISIONS Oct 17; it is the production path once verified) |
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
| M1 | Voice onboarding | Language pick + 6 spoken questions; profile card fills live; saved. Hindi and Telugu. The worker keeps 1 to 3 appliance types (`trades`); if he names more, Ustaad asks for his top 3 and never cuts the list silently. |
| M2 | Stuck mode: identify + guide | Golden nameplate + error photo → correct brand/model/code; spoken fix with source chip that plays the original note |
| M3 | Talk-back with captions | Every reply heard and shown as live captions in the worker's script; his words as a bubble; step card stays |
| M4 | Agent asks to see | Mid-repair photo request with framing tip; checked; continue or one retake with a reason |
| M5 | Safety gates | Hazardous step hidden until a photo passes; refrigerant → "certified gas technician needed"; skip attempts fail. A job with no card or manual source needs the mains-off photo before its first step; microwave high-voltage, picture-tube and geyser-opening work stop with a red screen. |
| M6 | WhatsApp import | Demo export (zip or loose files) → ≥20 fault cards with speaker, date, audio link, arriving live on the dashboard |
| M7 | Stock | "Do capacitor use kiye" decrements; repair checks stock first; low-stock badge |
| M8 | Parts quotes | Missing part → 3 vendor phones on Telegram → button/text/voice replies parsed and ranked → approve sends confirmations; < 2 min |
| M9 | Close job | "Ho gaya" → job log + new fault card with photo; stock updated |
| M10 | Judge-ready demo | "Try the demo": seeded worker, sample photos, cached golden paths; works in incognito on phone and laptop |

### Should (only after all Musts pass)
S1 manuals via Agent Search with page citations · S2 area cluster map (seeded, badged) · S3 Memory Bank coaching
nudges · S4 15 s video clips · S5 Tamil/Bengali polish · S6 pre-job brief · S7 Show Ustaad: worker-raised side
issues mid-repair (T36) and photos of the worker's own manual / wiring sticker (T37)

### Won't
Payments, native app, real auth, multi-team tenancy, other trades, continuous camera streaming, Gemma on-device,
reading WhatsApp groups directly.

### Cut order if behind
General-appliance tier (T38–T41) → S7 Show Ustaad → Live-look streaming → 15 s clips → Tamil/Bengali depth → shelf-photo counting → nudges as rules → map as table.
Never cut: M2–M5 (spoken + captioned guidance, agent-requested photos, safety gate), M6 import, M8 quotes.
The AC path comes first: the never-cut list must work for AC before the general-appliance tier is switched on.

## 4. WhatsApp knowledge import
No API reads groups. Use WhatsApp "Export chat → Include media".
- Paths: (a) share the export to the installed PWA (`share_target`; unverified that WhatsApp lists PWAs),
  (b) upload zip or loose files at `/d/import` (the demo path), (c) forward one voice note to the WhatsApp number (Should).
- Android: chat `.txt` + media, sometimes zipped. Voice notes `PTT-YYYYMMDD-WA####.opus`; line
  `12/05/25, 10:41 am - Ramesh: PTT-20250512-WA0003.opus (file attached)`.
- iOS: `.zip` with `_chat.txt`; lines `[12/05/25, 10:41:22 AM] Ramesh: …`. Date order varies by locale.
- Pipeline (Cloud Run Job `ingest-whatsapp`): upload to `gs://<bucket>/imports/{id}/` → parse messages → audio:
  `ffmpeg -i x.opus -ac 1 -ar 16000 x.flac` → Flash transcript `{text, language, confidence}` (keep Hinglish,
  codes and part numbers verbatim) → photos described → threads (Flash groups the messages, in time order, into question → answers → outcome; a
  reply can come hours later and a new fault can start minutes after the last, so time gaps are hints, not
  boundaries; splitting on 30-min gaps is only the fallback if the Flash call fails) → one card per
  resolved thread with sources → dedupe (same brand+code and cosine > 0.9 → merge, `verified_count++`) → embed →
  write; confidence < 0.6 → review queue. The extraction prompt sets `appliance_type`; an unclear type → review queue. Progress in `imports/{id}`. Target: 30 notes < 2 min, 8 parallel.
- Consent: only groups whose members agree. Strip phone numbers.

## 5. Architecture
PWA (Firebase Hosting, `/api/**` rewritten to Cloud Run) · Live voice opens `wss://` **directly** to the Cloud Run
URL (Hosting rewrites don't carry WebSockets; `--timeout=3600`, session affinity, origin check) · `ustaad-api`
(FastAPI + ADK) · Jobs `ingest-whatsapp`, `compute-clusters` · Agent Platform (Live, Flash, TTS, embeddings,
Memory Bank) · Agent Search (manuals) · Firestore + Storage · Places API (New) · Telegram Bot API.

Credits: ₹95.7k GenAI App Builder → Agent Search only (reportedly). ₹14.3k (≈Oct 24) and ₹1.5k (≈Oct 20) →
Gemini, Cloud Run, Firestore, Storage, Memory Bank. Card + alerts (₹500/2,000/5,000) after that.
Rate limits: 20 req/min per IP on `/api/chat` and `/ws/live`, 3 concurrent Live sessions.

Env: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`,
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `FLASH_MODEL`, `LIVE_MODEL`, `LIVE_LOCATION` (region for the Live client; the smoke test uses the same value), `EMBED_LOCATION` (optional region for embeddings; `global` was slower and at times past the 10 s timeout), `TTS_MODEL=gemini-3.8-flash-tts`,
`EMBED_MODEL=gemini-embedding-001`, `TRANSCRIBE_MODEL` (empty = Flash), `AGENT_ENGINE_ID`,
`AGENT_SEARCH_DATASTORE`, `TG_BOT_TOKEN`, `TG_WEBHOOK_SECRET`, `PLACES_API_KEY`,
`DEMO_SAFE`, `MEDIA_BUCKET`, `ALLOWED_ORIGINS`.

## 6. Agent
`build_ustaad(model)` → one ADK agent; Live via `runner.run_live()`, text via `runner.run_async()`; same tools.
Tools are framework-free functions in `backend/tools/` (fallback: raw `google-genai` Live client calls them).

| Tool | Input | Output | Live `behavior` / response scheduling |
| --- | --- | --- | --- |
| save_profile_fields | partial profile | profile | NON_BLOCKING, SILENT |
| identify_appliance | media_uri | brand, model, series, type (normalised to the `appliance_type` values), error_code, confidence, observations | BLOCKING |
| request_media | kind photo/video/document, target, reason, framing_tip, gate_id? | media_uri, findings, matches_expected, confidence, follow_up, retaking; answered once per checked photo on the same call (a retake reason, then the result); with gate_id, the gate check judges the photo instead (passed, reason) | NON_BLOCKING, WHEN_IDLE, long-running |
| search_fault_cards | brand, model?, error_code?, symptom?, appliance_type? | top 5 with citation {author, date, audio_uri}; an empty list when the best match is below the relevance floor | BLOCKING |
| search_manuals | query, brand, model? | snippets {text, doc, page} | BLOCKING |
| start_repair | job_id, card_ids; or, when no card or manual matched, proposed steps [{instruction, summary_en}] | steps {n, instruction, hazard none/HV/capacitor/refrigerant, source} | BLOCKING |
| next_step | job_id, observation, media_uri? | next step or SAFETY_GATE{gate_id, required_evidence} | BLOCKING |
| confirm_safety | (not a model tool) runs on each photo of a `request_media` with `gate_id` | passed, reason | — |
| check_inventory / update_inventory | part / [{part, delta}] | stock + low flags | BLOCKING / SILENT |
| find_vendors | part (location and pincode from his profile) | saved shop names + Places shops nearby, nearest first, with distance_km | BLOCKING |
| request_quotes | part, specs, qty (job and worker from session state; every saved vendor) | quote_request_id, vendor names | NON_BLOCKING, WHEN_IDLE |
| get_quotes / approve_quote | ids | ranked quotes / confirmation | BLOCKING |
| close_job | job_id, outcome, parts_used, fix_summary | job log + draft card id | BLOCKING |
| get_nudges / get_area_alerts | worker_id / pincode | nudges / clusters | BLOCKING |

Photo tools (`backend/models/tools.py`): the named fields are null when not legible; anything else worth knowing
goes in `observations` / `findings`, a list of {label, value, confidence} that code trims to the 6 surest at
confidence ≥ 0.6, so the agent sees more than fixed categories without a flood of guesses.
Set `behavior` explicitly on every function declaration (defaults differ between Live models). Scheduling
(WHEN_IDLE, SILENT) is set on the function response, not the declaration. Safety gates and copy: `docs/SAFETY.md`.
Instruction: patient senior technician; worker's language, Hinglish fine; one instruction at a time; ground fixes
in cards/manuals and say the source aloud; ask to see instead of guessing; never describe a hazardous step before
its gate; never give refrigerant steps or bypass safety devices; check stock before suggesting parts; end with close_job.
Safety in code: `next_step` returns SAFETY_GATE while a gate is open; `before_tool_callback` blocks next_step and
close_job with open gates; refrigerant and the other stop reasons → STOP_REFER; client shows a red screen with fixed
text for the reason (no audio).
Appliance types: one knowledge pool, tagged with `appliance_type` (`fault_card.schema.json`). One mapping constant
takes a profile `trades` value to card types (`ac` → `split_ac`, `window_ac`; the rest map to themselves). A job's
type comes from `identify_appliance` and is confirmed in conversation; the profile list is only a prior, and an
appliance outside it is still allowed. `search_fault_cards` filters by type in code after the vector query (fetch
the top 20, drop other types; no new Firestore index) and returns nothing below a named relevance-floor constant.
Source tiers: (1) fault card and (2) manual page are cited aloud. (3) General guidance is used only when 1 and 2
return nothing, and is said aloud as general guidance with no verified source. Tier 3 never gives an error-code
meaning, a component value or model-specific wiring: Ustaad says the code is not in its sources and asks to see the
manual page or wiring sticker. It prefers checks the worker can prove with a photo over assertions; photos only.
In every tier a repair step is spoken only after `next_step` has returned it.
General steps: with no card ids, the Live model passes its proposed steps to `start_repair`, each with `instruction`
(the worker's language) and `summary_en` (one line of English). No extra model call. The tool tags each step from
`summary_en` (hazard tagger, `docs/SAFETY.md`) and stores it on the job with source kind `general`; from then on
`next_step`, the gates and the callback treat it exactly like a card step.
Live: AUDIO modality, input + output transcription on, language from profile, session resumption, context
compression, PCM16 16 kHz in / 24 kHz out, push-to-talk.
Memory: Memory Bank (soft facts, end of session; PreloadMemoryTool) · Firestore (structured) · session state (job, step, gates).

## 7. Contracts (frozen Mon Oct 12, 12:00)
Firestore: `workers/{wid}` (+ `inventory`, `vendors`), `jobs`, `fault_cards`, `imports`, `quote_requests`, `quotes`,
`clusters`, `tg_updates` (dedupe), `demo_cache`. Field lists: `shared/contracts/firestore.md`. Fault card schema: `shared/contracts/fault_card.schema.json`.
REST request/response shapes: `shared/contracts/rest.md`. Changes: `shared/contracts/CHANGELOG.md`.
Vector index: `infra/firestore.sh`.
REST: `POST /api/demo/session` · `POST /api/chat` · `POST /api/media/upload-url` · `GET/POST /api/jobs`,
`GET /api/jobs/{id}` · `GET /api/fault-cards`, `GET/PATCH /api/fault-cards/{id}` · `GET/PATCH /api/inventory` ·
`GET/POST /api/vendors` · `POST /api/quotes/request`, `GET /api/quotes/{qrid}`, `POST /api/quotes/{qid}/approve` ·
`POST /api/imports`, `GET /api/imports/{id}` · `GET /api/clusters`, `/api/nudges`, `/api/dashboard/summary` ·
`POST /webhook/telegram` · `GET /healthz`.
WebSocket events: `shared/contracts/ws-events.md`.
Quotes per vendor: CREATED → SENT → PARSING → QUOTED → CONFIRMED; CLARIFY (one follow-up); EXPIRED (30 min);
DECLINED. Each vendor presses Start on the bot once before demos (a bot can only message chats that started it).

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
