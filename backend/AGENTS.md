# backend/ — local rules (the root AGENTS.md also applies)

- Layout: `app/` FastAPI (routers, `ws_live.py`, `telegram.py` vendor webhook) · `agent/` agent factory + instruction (human-owned) ·
  `tools/` pure functions · `models/` Pydantic contracts · `jobs/` Cloud Run Jobs.
- Each tool: `tools/<name>.py` + `tests/unit/test_<name>.py`. Inputs/outputs are models from `models/`.
- External calls go through one thin client per service (`clients/gemini.py`, `clients/firestore.py`, `clients/telegram.py`)
  so tests can swap in fakes. Never call SDKs directly from tools.
- Live tools: declare `behavior` (BLOCKING or NON_BLOCKING) explicitly on every function; set scheduling
  (WHEN_IDLE, SILENT) on the function *response*. Never rely on the model's default (DECISIONS.md).
- Embeddings: `EMBED_MODEL` with `output_dimensionality=EMBED_DIM` (768).
- Repair steps and gates: follow `docs/SAFETY.md` exactly; its 10 bypass tests live in `tests/unit/test_safety.py`.
- ADK instruction placeholders use `{key?}` so a missing state key never crashes a session.
- Webhooks: verify the signature or secret, return 200 immediately, process in the background, dedupe on the delivery ID.
- Local env: `backend/.env` (copy `.env.example`); `make dev-api` loads it.
- Tests: `make test` (unit, no network). Golden-path tests with real models: `make golden` (costs money; run before `demo` deploys only).
