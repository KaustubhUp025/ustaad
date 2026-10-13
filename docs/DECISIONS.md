# Decisions log

Add a line whenever something in SPEC §1 is decided or changed. Newest at the top. Agents: don't reopen a
decision here; if you think one is wrong, say so in your final message.

| Date | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| 2026-10-13 | `LIVE_MODEL=gemini-3.8-live`, `LIVE_LOCATION=us-central1` | T05 smoke test passed 3 runs in hi/te/ta/bn plus a tool call and a Hindi clip; the model is not found in `global` or `asia-south1` for this project | it appears in an India or global location, or latency on 4G misses the 2.5 s target |
| 2026-10-13 | Live sessions name the reply language and script in the system instruction, not only in `speech_config.language_code` | with `language_code` alone the Tamil output transcript came back in Latin letters | — |
| 2026-10-13 | Add S7 Show Ustaad (side issues T36, manual photo T37) as Should, lane A | real jobs surface second problems and owner manuals; reuses request_media | Musts slip past Wed integration gate |
| 2026-10-11 | Live tools declare `behavior` explicitly on every function (BLOCKING or NON_BLOCKING); scheduling (WHEN_IDLE, SILENT) is set on the function response | Default differs between Live models (3.8 Live documents async as default; older models block) | — |
| 2026-10-11 | Embeddings: `gemini-embedding-001` with `output_dimensionality=768` | model default is 3072; Firestore index is 768 | retrieval quality is poor |
| 2026-10-11 | Repo copies of SPEC/TASKS are authoritative for agents; the shared doc mirrors them | agents can't read external docs | — |
| 2026-10-11 | Repo is tool-neutral; AGENTS.md is the only rule source | two people, different AI tools | — |
| 2026-10-11 | Contracts flow: `shared/contracts/*.md` → Pydantic in `backend/models/` → `make types` → openapi.json + TS types | one direction, CI drift check | — |
| 2026-10-11 | Transcription: ffmpeg → 16 kHz mono FLAC → Flash | `audio/ogg` not a listed input type; Transcribe model is preview on another API | Transcribe GA on Vertex |
| 2026-10-11 | Live voice connects straight to Cloud Run | Hosting rewrites don't carry WebSockets | — |
| 2026-10-11 | Gemini only via Agent Platform (Vertex) | Cloud credits don't pay for AI Studio keys | — |
| 2026-10-11 | Design: tool-derived palette, 7-segment code readout as signature | first palette was a generic default | — |
