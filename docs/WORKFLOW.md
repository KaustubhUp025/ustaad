# Ustaad — team workflow (2 people + AI coding agents, any tools)

Task board: `docs/TASKS.md` (authoritative). The shared "Team workflow" doc tab mirrors it for humans.
This repo is tool-neutral: every person may use any AI coding agent or model. What's fixed is the repo — rules
(`AGENTS.md`), playbooks (`docs/playbooks/`), commands (`make`), contracts and CI.

## Who owns what

| | A — Voice & Agent (Kaustubh, @KaustubhUp025) | B — Knowledge & Commerce (Samyak, @samyak8796) |
| --- | --- | --- |
| Features | M1, M2, M3, M4, M5, M9, S3 | M6, M7, M8, M10, S1, S2 |
| Backend | `agent/`, `app/ws_live.py`, tools: identify, request_media, repair steps, safety, close_job, memory | `jobs/`, `wa/`, tools: fault-card search, manuals, inventory, vendors, quotes, clusters |
| Frontend | design-system pass (tokens → Tailwind theme, base components), `web/src/audio`, `/w/start`, `/w/onboard`, `/w/job/:id` | app shell, `/w` home, `/w/stock`, quotes card, all `/d/*` pages, built on A's components |
| Infra | Live smoke tests, Memory Bank instance, `demo` deploys | GCP project, CI, Firestore + indexes, Agent Search, Meta app, `dev` deploys |
| Content | system instruction, safety copy | seed data, voice-note script, i18n files, deck |

Swap whole columns if you prefer, never single rows. Interfaces between you: tool contracts (SPEC §6) and UI
contracts (SPEC §7). B ships tool stubs with fixtures by Mon 12:00; A ships `MOCK_LIVE=1` (replays a recorded
session) so B's UI work never needs a live model.

## Gates
- **Mon Oct 12, 12:00** contracts frozen (`shared/contracts/` merged, stubs + mock live).
- **Wed Oct 14, 21:00** integration: G2 + G3 end to end on a real phone on `dev`.
- **Thu Oct 15, 18:00** feature freeze. **Sat Oct 17, 21:00 IST** submit.
Critical path: Hindi Live voice (A, Mon) → tool calls over Live (A, Tue) → import → searchable cards (B, Tue) → G2 (Wed).

## How AI agents fit in

### One source of rules, thin adapters
| File | Role |
| --- | --- |
| `AGENTS.md` (+ `backend/AGENTS.md`, `web/AGENTS.md`) | The only rules. Many agents read AGENTS.md natively; folder files keep context small. |
| `CLAUDE.md`, `GEMINI.md` | Adapters for tools that look for those names; they only point to AGENTS.md. |
| `.claude/commands/*` | Shortcuts that call the playbooks; other tools just say "Follow docs/playbooks/<x>.md". |
| `docs/PRODUCT.md`, `TASKS.md`, `SAFETY.md`, `GOLDEN_PATHS.md`, `GLOSSARY.md`, `DECISIONS.md`, `STATUS.md` | The aim, the plan, the hard rules and the current state, so no agent needs an external doc. |
| `docs/playbooks/task.md`, `review.md`, `ui-pass.md` | How to do a task, review a PR, build a screen — identical for every tool. |
| `Makefile` | `make check` / `make test` / `make dev-*` — one command set for every tool and person. |

Adding another tool later = one adapter file that says "follow AGENTS.md". Never copy rules into an adapter.

### Cross-model review
Every PR is reviewed by a **different model** from the one that wrote it (`docs/playbooks/review.md`). The PR
template records both. In practice each of you reviews the other's PRs with whatever tool you use, or uses a
second model yourself. CI (`make check`) is the referee: a model's approval never overrides red CI. Contract PRs
need both humans plus one model review.

### Getting the most out of any tool
- **Small, well-cited task cards** (playbook template): the agent reads 3–5 named files, not the repo.
- **Folder-level AGENTS.md** keeps each session's context to the part of the codebase it touches.
- **Fresh session per task**; long sessions accumulate stale context and slow down.
- **Fixtures and mocks** (`seed/fixtures/`, `MOCK_LIVE=1`) so agents run tests offline in seconds, not against paid APIs.
- **`make check` is fast and deterministic**, so agents verify by running, not by reasoning.
- **Parallel worktrees** for independent tasks; limit parallelism by how much you can review, not by tool.
- **Humans own** contracts, the agent instruction, safety code and AGENTS.md; agents propose, humans merge.
- If one tool is unavailable or slow at any moment, switch tools mid-task: the rules, playbooks and commands are the same.

## Daily rhythm (IST)
09:30 sync (15 min) → build → 14:00 contract check (15 min) → build → 21:00 merge, deploy `dev`, run golden
paths, one line in `docs/STATUS.md` → 22:30 stop.

## Definition of done
Merged to `main`, CI green, on `dev`; acceptance check passes on a real phone (UI) or a test (backend); strings in
i18n; no secrets; golden paths still pass; reviewed by a different model; status Done on the task board.

## Tonight (Sun Oct 11)
- [ ] T01 confirm team registration (closes today) — both
- [ ] T02 create the public GitHub repo from this starter, add teammate, branch protection on `main` — B
- [ ] T03 `infra/setup.sh`: project, APIs, Firestore, bucket, budgets — B
- [ ] T04 deploy `/healthz` + PWA shell — A
- [ ] T05 Live smoke test in hi/te/ta/bn → set `LIVE_MODEL` — A
- [ ] T06 Meta app + WhatsApp test number + 5 recipients — B
- [ ] T07 test sharing a WhatsApp export to the installed PWA on both phones — B
- [ ] T08 voice-note script; start recording (`seed/voice_note_script.md`) — B, A helps
