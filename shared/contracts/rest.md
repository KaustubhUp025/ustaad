# REST contract v1 (`ustaad-api`)

Owner: B (A owns `/api/chat` and `/api/demo/session`). Frozen Mon Oct 12, 12:00.
Source of truth flow: **this file → Pydantic models in `backend/models/` → `make types` →
`shared/contracts/openapi.json` + `web/src/api/types.ts`**. CI fails if the generated files are stale.
All JSON. Auth: `Authorization: Bearer <session token>` except `/healthz`, `/api/demo/session` and the webhook.
Errors use `{"error": {"code": "<stable code>", "message": "<safe message>"}}` with the matching HTTP status.
Allowed codes are `bad_request` (400), `unauthorized` (401), `forbidden` (403), `not_found` (404),
`conflict` (409), `validation_error` (422), `rate_limited` (429), `internal_error` (500), and `http_error`
(other explicitly raised HTTP statuses). Messages are fixed by code and never include submitted values, IDs,
numbers, exception text, request-validation details, tracebacks, credentials, secrets, or implementation details.

| Method + path | Request | Response |
| --- | --- | --- |
| `POST /api/demo/session` | `{"worker_id": "w_hi_demo"}` (optional; default Hindi demo worker) | `{"token": "…", "worker": Worker, "ws_url": "wss://…/ws/live"}` — token is a signed, 24 h demo token |
| `POST /api/chat` | `{"job_id": "j_1", "text": "…"}` or `{"job_id", "audio_uri": "gs://…"}` | `{"text": "…", "events": [WsServerFrame], "tts_url": "https://… signed" or null}` — same events as the WebSocket |
| `POST /api/media/upload-url` | `{"kind": "photo"\|"video"\|"import", "content_type": "image/jpeg", "job_id"?: "j_1", "import_id"?: "i_1", "request_id"?: "r_1", "filename"?: "x.zip"}` | `{"upload_url": "https://… signed PUT", "uri": "gs://…", "expires_in": 900, "headers": {"Content-Type": "image/jpeg", "x-goog-content-length-range": "0,15728640"}}` |
| `GET /api/jobs` | — | `{"items": [Job]}` (this worker, newest first) |
| `POST /api/jobs` | `{"appliance"?: {...}, "symptom"?: "…"}` | `Job` |
| `GET /api/jobs/{id}` | — | `Job` |
| `GET /api/fault-cards?q=&brand=&code=&status=&appliance_type=` | — (`appliance_type`: optional, one `appliance_type` value from `fault_card.schema.json`) | `{"items": [FaultCard], "next": cursor\|null}` |
| `GET /api/fault-cards/{id}` | — | `FaultCard` |
| `PATCH /api/fault-cards/{id}` | `{"review_status": "approved"\|"rejected", "edits"?: {...}}` | `FaultCard` |
| `GET /api/inventory` | — | `{"items": [InventoryItem]}` |
| `PATCH /api/inventory` | `{"deltas": [{"part": "capacitor 2.5uF", "delta": -2}]}` | `{"items": [InventoryItem]}` |
| `GET /api/vendors` / `POST /api/vendors` | — / `Vendor` (no id) | `{"items": [Vendor]}` / `Vendor` |
| `POST /api/quotes/request` | `{"job_id", "part", "specs", "vendor_ids": []}` | `QuoteRequest` |
| `GET /api/quotes/{qrid}` | — | `{"request": QuoteRequest, "quotes": [Quote]}` |
| `POST /api/quotes/{qid}/approve` | — | `{"request": QuoteRequest, "quotes": [Quote]}` |
| `POST /api/imports` | `{"uris": ["gs://…"], "group_name"?: "AC Mistri Noida"}` | `Import` (status `queued`) |
| `GET /api/imports/{id}` | — | `Import` |
| `GET /api/clusters?pincode=` | — | `{"items": [Cluster]}` |
| `GET /api/nudges` | — | `{"items": [{"id", "text", "kind": "skill"\|"restock", "action"?: {...}}]}` |
| `GET /api/dashboard/summary` | — | `{"cards": int, "cards_needing_review": int, "jobs_7d": int, "imports": int}` |
| `GET /webhook/whatsapp` | Meta verify query | `hub.challenge` |
| `POST /webhook/whatsapp` | Meta payload, `X-Hub-Signature-256` checked | `200` at once; processed in background |
| `GET /healthz` | — | `{"ok": true, "flash_model", "live_model", "demo_safe"}` |

Entity shapes (Worker, Job, FaultCard, InventoryItem, Vendor, QuoteRequest, Quote, Import, Cluster) are the
Firestore documents in `firestore.md` plus `id`, minus server-only fields (`embedding`, raw webhook bodies).

## Media upload URL validation

The browser must send every header returned in `headers` with the signed PUT. Both returned headers are part of
the V4 signature. Allowed content types and binary size limits are:

| Kind | Content types | Maximum bytes |
| --- | --- | ---: |
| `photo` | `image/jpeg`, `image/png` | 15,728,640 (15 MiB) |
| `video` | `video/mp4` | 52,428,800 (50 MiB) |
| `import` | `application/zip`, `audio/ogg`, `audio/opus`, `text/plain`, `image/jpeg`, `image/png` | 104,857,600 (100 MiB) |

An unsupported content type, or a listed type used with the wrong kind, returns HTTP 400.

A photo or video that answers a `media_request` passes that request's `request_id` (`r_` + letters and digits). The
object is stored under `jobs/{job_id}/{request_id}/`, and the server accepts a `media_ready` only for a `uri` in that
request's own folder, so a photo uploaded for one request cannot answer another (ws-events.md).

## Inventory validation (T10 approved slice)

`InventoryItem` follows the inventory validation rules in `firestore.md`, including
required nullable `category` and `unit_cost_inr`. All fields below are required without
defaults; reject unknown fields at every inventory object level.
The list response's `items` is an array (empty allowed). The delta request's `deltas`
is a nonempty array. Each delta has `part` (nonblank name or alias) and `delta`
(strict nonzero signed integer; reject booleans, strings and floats).

Voice compatibility belongs at the `update_inventory` tool boundary, before strict
Pydantic validation: normalize finite whole-valued floats (e.g. `2.0`) to integers;
reject fractional values, booleans, strings, NaN/infinity and zero. This does not change
REST validation or the tool's existing input shape in SPEC §6. No tool wrapper exists
in this slice, so voice normalization integration remains pending for T18.
Routes, part lookup, persistent stock updates and negative-stock enforcement are deferred.
