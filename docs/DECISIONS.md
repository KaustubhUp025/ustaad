# Decisions log

Add a line whenever something in SPEC §1 is decided or changed. Newest at the top. Agents: don't reopen a
decision here; if you think one is wrong, say so in your final message.

| Date | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| 2026-10-16 | LG sources: AC error codes from the LG Room Air Conditioner service manual MFL41161601 (general wall-mounted inverter; code tables printed pp.46–48, CH05 communication per p.57); washing-machine codes (OE, IE, UE) from LG's official lg.com support pages, kept as dated PDFs. Voltas from the owner's manual (table p.30), Daikin from service manual SiUS091133 (US models, table p.94) | no other LG home split AC manual with the CH table was found, and LG's washer codes are published only on lg.com; each code in the T08 script is traced to one of these and checked by a person (Kaustubh, Oct 16) | an India-model manual is found for any of the three brands |
| 2026-10-13 | Other household appliances (fridge, washing machine, LED TV, microwave, geyser, fan/cooler) get a labelled general-guidance tier through the same tools and gates as AC; no web search, no extra model call; stop screens are text only, with no audio clip | the knowledge is all AC and the agent had no defined behaviour when no card or manual matched | the never-cut list is not working for AC by the Wed integration gate: cut this tier first |
| 2026-10-13 | Agents read only their task's section of docs/BUILD-GUIDE.md; repo docs win on conflict | lets a task be started with just its ID | guide drifts from SPEC |
| 2026-10-13 | English is a fifth profile language (`en`): the worker can pick it at onboarding and Ustaad then speaks English | a Hindi-profile session answers in Hindi even to an English question, and judges will speak English; `workers.lang` already allows `en`; an `en-IN` Live turn passed the smoke test | — |
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
