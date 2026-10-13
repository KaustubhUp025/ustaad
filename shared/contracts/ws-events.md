# Live WebSocket protocol v1 — `wss://<cloud-run-url>/ws/live?token=<session-token>&lang=hi&job_id=j_1`

Owner: A. Frozen Mon Oct 12, 12:00. Changes: PR reviewed by both people + an entry in `CHANGELOG.md`.
Binary frames are raw audio. Text frames are JSON objects with `"v": 1` and a `"type"`.
The client connects straight to Cloud Run (Firebase Hosting rewrites don't carry WebSockets).

## Client → server
| type | Example |
| --- | --- |
| (binary) | PCM16 mono 16 kHz, 40 ms chunks, only between `ptt start` and `ptt end` |
| `ptt` | `{"v":1,"type":"ptt","state":"start"}` / `"end"` |
| `media_ready` | `{"v":1,"type":"media_ready","request_id":"r_1","uri":"gs://bucket/jobs/j_1/r_1.jpg","kind":"photo"}` (`kind`: `photo`\|`video`\|`document`) |
| `media_cancel` | `{"v":1,"type":"media_cancel","request_id":"r_1"}` |
| `text` | `{"v":1,"type":"text","text":"PCB nahi hai"}` (typed fallback) |
| `ping` | `{"v":1,"type":"ping"}` every 20 s |

## Server → client
| type | Example | Notes |
| --- | --- | --- |
| (binary) | PCM16 mono 24 kHz | Ustaad's voice |
| `session_ready` | `{"v":1,"type":"session_ready","session_id":"s_1","live_model":"gemini-3.8-live","resumable":true}` | first frame |
| `caption` | `{"v":1,"type":"caption","who":"ustaad","text":"Pehle MCB band karo","final":false}` | partials replaced by the final; `who`: `user` or `ustaad` |
| `turn_complete` | `{"v":1,"type":"turn_complete"}` | |
| `interrupted` | `{"v":1,"type":"interrupted"}` | barge-in: client stops playback and clears its buffer |
| `profile_update` | `{"v":1,"type":"profile_update","fields":{"brands":["Voltas","LG"],"pincode":"201301"}}` | M1: profile card fills live |
| `identified` | `{"v":1,"type":"identified","brand":"Voltas","model":"183V CZQ","error_code":"E6","confidence":0.9}` | drives the code readout |
| `step_card` | `{"v":1,"type":"step_card","job_id":"j_1","n":3,"of":6,"instruction":"Capacitor par meter lagao","hazard":"capacitor","source":{"kind":"whatsapp_voice","label":"Ramesh · May 2025","audio_uri":"gs://…/PTT-20250512-WA0003.flac","doc":null,"page":null}}` | `source.kind`: `whatsapp_voice`\|`whatsapp_text`\|`manual`\|`job`\|`synthetic` (as `source.type` in `fault_card.schema.json`) \|`manual_photo` (the worker's own photographed manual page or wiring sticker) |
| `media_request` | `{"v":1,"type":"media_request","request_id":"r_1","kind":"photo","target":"Outdoor PCB, capacitor ke paas","framing_tip":"Flash on, 20 cm door","max_seconds":null}` | `kind`: `photo`\|`video`\|`document` (a manual page or wiring sticker); `max_seconds` 15 for video |
| `media_result` | `{"v":1,"type":"media_result","request_id":"r_1","matches_expected":false,"confidence":0.41,"retake_reason":"Photo dhundhli hai, thoda paas se"}` | `retake_reason` null when OK |
| `safety_gate` | `{"v":1,"type":"safety_gate","gate_id":"G_CAP_DISCHARGE","message":"Capacitor discharge karo","required_evidence":"Multimeter 0V photo"}` | gate IDs in docs/SAFETY.md |
| `gate_result` | `{"v":1,"type":"gate_result","gate_id":"G_CAP_DISCHARGE","passed":true,"reason":null}` | |
| `safety_stop` | `{"v":1,"type":"safety_stop","reason":"refrigerant","message":"Certified gas technician chahiye"}` | full red screen |
| `tool_activity` | `{"v":1,"type":"tool_activity","label":"Stock check kar raha hoon"}` | |
| `stock` | `{"v":1,"type":"stock","part":"Outdoor PCB","qty":0,"min_qty":1,"low":true}` | |
| `quotes` | `{"v":1,"type":"quotes","quote_request_id":"qr_1","items":[{"quote_id":"q_1","vendor":"Sharma Electricals","distance_km":1.8,"price_inr":3400,"available":true,"eta":"45 min","from_voice":true}]}` | sent again as replies arrive |
| `job_closed` | `{"v":1,"type":"job_closed","job_id":"j_1","card_id":"fc_123"}` | |
| `resume_handle` | `{"v":1,"type":"resume_handle","handle":"opaque"}` | client reconnects with `&resume=<handle>` |
| `pong` | `{"v":1,"type":"pong"}` | |
| `error` | `{"v":1,"type":"error","code":"live_unavailable","message":"…"}` | codes: `live_unavailable`, `rate_limited`, `auth`, `bad_request` |

Mock: with `MOCK_LIVE=1` (server) or `VITE_MOCK_LIVE=1` (client), `seed/fixtures/live_session.jsonl` is replayed:
one JSON object per line, `{"t_ms": 1200, "frame": {…server frame…}}`; audio frames are omitted.
