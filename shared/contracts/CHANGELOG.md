# Contracts changelog

Every change to a file in `shared/contracts/` adds a line here in the same PR (both people approve).

| Date | File | Change | Author | Approved by |
| --- | --- | --- | --- | --- |
| 2026-10-11 | all | v1 drafts: ws-events, rest, firestore, fault_card schema | setup | — |
| 2026-10-13 | ws-events.md | `media_request.kind` and `media_ready.kind` accept `document`; `step_card.source.kind` accepts `manual_photo`; allowed values listed (S7, T37) | A | B (PR #7) |
| 2026-10-13 | firestore.md | `jobs.media[]` gets optional `reason` (`requested`\|`side_issue`\|`manual`); `media[].kind` values listed (`photo`\|`video`\|`document`) (S7, T36/T37) | A | B (PR #7) |
| 2026-10-13 | fault_card.schema.json | `appliance_type` also accepts `led_tv`, `microwave`, `geyser`, `fan_cooler`; the five existing values are unchanged, so existing cards stay valid (T38) | A | |
| 2026-10-13 | firestore.md | `workers.trades[]` is 1 to 3 values, no duplicates, from a listed set; `jobs.appliance.type` uses the `appliance_type` values; `jobs.steps[].source.kind` values named, including `general` (T38) | A | |
| 2026-10-13 | ws-events.md | `step_card.source.kind` accepts `general` (general guidance with no verified source) (T38) | A | |
| 2026-10-13 | rest.md | `GET /api/fault-cards` takes an optional `appliance_type` filter (T38) | A | |
| 2026-10-14 | rest.md | Upload URL responses include the exact signed PUT headers; kind-specific content types and binary size limits are fixed | B (Samyak) | A (Kaustubh) and B (Samyak) |
| 2026-10-13 | firestore.md, rest.md | T10 inventory only: required strict fields, nullable category/price, UTC, part_ IDs, list/delta validation; whole-float normalization at future voice boundary | B (Samyak) | A (Kaustubh), explicit approval relayed by Samyak; inventory only |
| 2026-10-13 | openapi.json (unchanged), generated web/src/api/types.ts | Run make types; commit existing health-route TypeScript baseline; inventory schemas await routes | B | No contract change |
| 2026-10-15 | firestore.md | `jobs.current_step` (int): which step `next_step` hands out next, so a reconnect or a parked repair resumes at the same step (T16, T36) | A | A (Kaustubh) and B (Samyak) |
| 2026-10-15 | rest.md | Define the shared REST error envelope, stable codes, and fixed safe public messages | B (Samyak) | A (Kaustubh) and B (Samyak) |
| 2026-10-15 | ws-events.md | `media_offer` (client): the worker starts a photo himself; the server answers with `media_request`. `media_request` also comes from the server for an open safety gate, and open requests are sent again after a reconnect with `resume` to the same server instance (without it, only safety-gate and worker-started requests; on another instance, only the gate request) (T17) | A | A (Kaustubh); B (Samyak) pending until the PR #25 review is resolved |
| 2026-10-15 | rest.md, openapi.json, generated web/src/api/types.ts | `POST /api/media/upload-url` takes an optional `request_id`; a request's photos are stored under `jobs/{job_id}/{request_id}/`, and `media_ready` must use that folder (PR #25 review: no photo replay across requests) | A | A (Kaustubh); B (Samyak) pending |
