# Ustaad — rules for every coding agent

These rules apply to any AI coding agent or assistant used on this repo, and to humans. No tool or model is
preferred; tool-specific files (`CLAUDE.md`, `GEMINI.md`, `.claude/`, …) are thin adapters that point here.

Ustaad is a voice-first assistant for Indian AC and appliance repair technicians, built for the Google Cloud AI
Builder Cup 2026. Submission: Sat Oct 17, 21:00 IST. Feature freeze: Thu Oct 15, 18:00.

## Read in this order (only what your task needs)
1. `docs/PRODUCT.md` — the aim, the user, how we're judged (once per session, for behaviour/UI/copy tasks)
2. `docs/TASKS.md` — your task's row: priority, the files to read, done-when
3. The `docs/SPEC.md` sections and `shared/contracts/` files that row names
4. The folder's own `AGENTS.md` (`backend/`, `web/`)
5. As needed: `docs/SAFETY.md` (any repair-step code), `docs/GOLDEN_PATHS.md` (demo flows), `docs/DESIGN.md`
   (UI), `docs/GLOSSARY.md` (terms and Hinglish), `docs/DECISIONS.md` (settled choices), `docs/STATUS.md` (what works)

The repo is authoritative. If code, a task card and the spec disagree, stop and ask a human.

## Commands (same for every tool)
`make check` before you finish (lint + unit tests + TS typecheck + build) · `make test` · `make types` after any
model/contract change · `make dev-api` / `make dev-web` · `make help` for the rest. Don't invent other commands.

## Stack
Python 3.12 + uv + FastAPI + google-adk + google-genai (Vertex / Agent Platform) ·
Vite + React 19 + TypeScript + Tailwind + shadcn/ui + react-i18next + vite-plugin-pwa ·
Cloud Run, Cloud Run Jobs, Firestore, Cloud Storage, Firebase Hosting.

## Contracts flow (one direction)
`shared/contracts/*.md|json` (human-approved) → Pydantic models in `backend/models/` → `make types` →
`shared/contracts/openapi.json` + `web/src/api/types.ts` (generated; never edit by hand). CI fails on drift.

## Never
- Edit `shared/contracts/`, `docs/SAFETY.md`, `backend/agent/instruction.md`, `backend/agent/callbacks.py`,
  `docs/DECISIONS.md` or this file unless the task says so.
- Call Gemini with AI Studio keys; always Vertex (`GOOGLE_GENAI_USE_ENTERPRISE=TRUE`, `GOOGLE_GENAI_USE_VERTEXAI=TRUE`).
- Hard-code model IDs or embedding size; read `FLASH_MODEL`, `LIVE_MODEL`, `TTS_MODEL`, `EMBED_MODEL`, `EMBED_DIM`.
- Call real Gemini, WhatsApp or Places APIs in unit tests; use `seed/fixtures/` and fake clients.
- Write secrets, tokens, real phone numbers or customer data anywhere.
- Invent error-code meanings or repair steps; they come from manuals or recorded notes only.
- Add a dependency without naming it in your final message.
- Put user-facing strings outside `web/src/i18n/*.json`, or colours/fonts outside `web/src/styles/tokens.css`.
- Emit or render a hazardous repair step before its gate passes (`docs/SAFETY.md`).

## Always
- Tools in `backend/tools/` are pure functions: Pydantic in, Pydantic out, one unit test each.
- Commit prefix: the feature ID (`M4: …`) or, for tasks without one, the task ID (`T03: …`).
- Update your task's Status in `docs/TASKS.md` in the same PR.
- UI work follows `docs/playbooks/ui-pass.md`.
- Finish with: what changed, how to test it, what you were unsure about.

## Simplicity (no speculative code)
- Write the least code that meets the task's done-when. No base classes, factories, registries, plugin systems,
  config flags or retry/caching layers unless the task asks.
- No unused functions, params, files or TODOs. No comments that restate the code; comment only the why.
- Prefer editing existing code over adding new modules. Don't refactor outside the task.
- Don't add error handling for cases that can't happen; let unexpected errors raise.
- If you think an abstraction is needed, say so in your final message instead of adding it.

## Verification (evidence, not claims)
- Red first: write the new test, run it, show it failing for the right reason, then implement.
- Never edit, weaken, skip or xfail an existing test to make it pass. If one seems wrong, stop and say so.
- Mock only external services (Gemini, WhatsApp, Places, GCS, Firestore); never mock the function under test.
- Check any google-adk / google-genai / FastAPI API you're unsure of against the installed package source
  (`uv run python -c "import inspect; ..."`) before using it. Don't trust memory.
- Done = `make check` green AND you ran the thing (curl the endpoint, replay the fixture, or screenshot the
  screen). Paste the summary line and the evidence in your final message.
- Final message also lists: files changed with line counts, and anything you added that the task didn't ask for
  (should be nothing).

## Work efficiently (keeps any tool fast and cheap)
- Open only the files your task row lists. Don't scan the whole repo.
- One task = one branch = one worktree = one fresh session.
- Plan briefly, write tests, then code. Verify by running `make test`, not by reasoning.
- Keep diffs small (< ~300 lines). If a task grows, stop and propose a split.
- Reference files by path instead of pasting large files, logs or schemas into the conversation.
