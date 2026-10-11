# REST contract v1 (`ustaad-api`)

Owner: B (A owns `/api/chat` and `/api/demo/session`). Frozen Mon Oct 12, 12:00.
Source of truth flow: **this file → Pydantic models in `backend/models/` → `make types` →
`shared/contracts/openapi.json` + `web/src/api/types.ts`**. CI fails if the generated files are stale.
All JSON. Auth: `Authorization: Bearer <session token>` except `/healthz`, `/api/demo/session` and the webhook.
Errors: `{"error": {"code": "not_found", "message": "…"}}` with the matching HTTP status.

| Method + path | Request | Response |
| --- | --- | --- |
| `POST /api/demo/session` | `{"worker_id": "w_hi_demo"}` (optional; default Hindi demo worker) | `{"token": "…", "worker": Worker, "ws_url": "wss://…/ws/live"}` — token is a signed, 24 h demo token |
| `POST /api/chat` | `{"job_id": "j_1", "text": "…"}` or `{"job_id", "audio_uri": "gs://…"}` | `{"text": "…", "events": [WsServerFrame], "tts_url": "https://… signed" or null}` — same events as the WebSocket |
| `POST /api/media/upload-url` | `{"kind": "photo"\|"video"\|"import", "content_type": "image/jpeg", "job_id"?: "j_1", "import_id"?: "i_1", "filename"?: "x.zip"}` | `{"upload_url": "https://… signed PUT", "uri": "gs://…", "expires_in": 900}` |
| `GET /api/jobs` | — | `{"items": [Job]}` (this worker, newest first) |
| `POST /api/jobs` | `{"appliance"?: {...}, "symptom"?: "…"}` | `Job` |
| `GET /api/jobs/{id}` | — | `Job` |
| `GET /api/fault-cards?q=&brand=&code=&status=` | — | `{"items": [FaultCard], "next": cursor\|null}` |
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
