# Firestore contract v1

Databases: `(default)` for dev, `demo` for the judged deployment (`FIRESTORE_DB`). Times are UTC ISO-8601
timestamps; money is integer rupees; IDs are prefixed strings (`w_`, `j_`, `fc_`, `qr_`, `q_`, `i_`, `part_`).
Only the backend reads and writes Firestore. The web app never talks to Firestore directly: live import progress
and live quotes are polled over REST (`GET /api/imports/{id}`, `GET /api/quotes/{qrid}`) every 2 s while visible.
(No Firebase Auth is used, so Firestore security rules could not verify our demo session token.)
Deploy `firestore.rules` that deny all client access.

| Collection | Fields |
| --- | --- |
| `workers/{wid}` | name, lang (`hi`\|`te`\|`ta`\|`bn`\|`en`), trades[] (1 to 3 values, no duplicates, from `ac`\|`fridge`\|`washing_machine`\|`led_tv`\|`microwave`\|`geyser`\|`fan_cooler`\|`other`), brands[], pincode, geo{lat,lng}, experience_yrs, onboarding_done, skill_gaps[], demo (bool), created_at |
| `workers/{wid}/inventory/{part_id}` | name, aliases[], category, qty, min_qty, unit_cost_inr, source (`voice`\|`photo`\|`manual`), updated_at |
| `workers/{wid}/vendors/{vid}` | name, wa_phone (E.164, never committed to git), place_id, pincode, categories[], reliability (0–1) |
| `jobs/{jid}` | worker_id, pincode, appliance{brand, model, series, type (an `appliance_type` value from `fault_card.schema.json`, or null)}, error_code, symptom, status (`open`\|`guiding`\|`waiting_part`\|`closed`), steps[{n, instruction, hazard, source}] (`source.kind` as `step_card.source.kind` in `ws-events.md`, including `general`), gates{gate_id: `open`\|`passed`\|`failed`}, media[{request_id, uri, kind (`photo`\|`video`\|`document`), findings, confidence, reason (optional: `requested`\|`side_issue`\|`manual`)}], card_ids_used[], parts_used[{part, qty}], outcome, seeded, created_at, closed_at |
| `fault_cards/{cid}` | `fault_card.schema.json` fields + `embedding` (Vector, 768, server-only) |
| `imports/{iid}` | worker_id, group_name, status (`queued`\|`parsing`\|`transcribing`\|`extracting`\|`done`\|`failed`), files_total, audio_total, audio_done, threads, cards_created, cards_needing_review, errors[], started_at, finished_at |
| `quote_requests/{qrid}` | job_id, worker_id, part, specs, vendor_ids[], status (`open`\|`approved`\|`expired`), approved_quote_id, created_at, expires_at |
| `quote_requests/{qrid}/quotes/{qid}` | vendor_id, vendor_name, state (`CREATED`\|`SENT`\|`PARSING`\|`CLARIFY`\|`QUOTED`\|`CONFIRMED`\|`DECLINED`\|`EXPIRED`), price_inr, available, eta, from_voice, raw_text, media_uri, parsed_confidence, updated_at |
| `clusters/{key}` | model, component, pincodes[], count, window_days, z_score, hypothesis, seeded, computed_at |
| `wa_messages/{wamid}` | direction, from_hash, type, body, media_id, quote_request_id, ts (doc ID = WhatsApp message ID, so retries dedupe) |
| `demo_cache/{hash}` | request_hash, response, model, created_at |

## Inventory validation (T10 approved slice)

All inventory entity fields are required with no defaults; unknown fields are rejected.
The REST entity includes `id`: a `part_`-prefixed string with a nonempty, non-whitespace
suffix, matching the inventory document ID (`part_id`). The persistence boundary must
check that equality when loading/writing documents; this model-only slice has no document lookup.
`name` is nonblank; `category` is null or nonblank; `aliases` is an array of nonblank
strings (empty allowed). `qty` and `min_qty` are strict nonnegative integers.
`unit_cost_inr` is null for an unknown price or a strict nonnegative integer in rupees;
never default an unknown price to zero. Strict integers reject booleans, strings and floats.
`source` is `voice`, `photo` or `manual`. `updated_at` is timezone-aware UTC: accept
ISO-8601 `Z` or `+00:00`, serialize as `Z`; reject naive timestamps and nonzero offsets.
