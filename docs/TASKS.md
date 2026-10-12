# Task board (repo copy — authoritative for agents)

Update the Status column in your PR when a task changes state (`todo` → `doing` → `done` / `blocked`).
Priority: **P0** = on the never-cut list or the critical path · **P1** = Must feature · **P2** = Should.
"Read" = the only files an agent needs to open for that task (plus AGENTS.md and the folder's AGENTS.md).
Commit prefix: the feature ID if there is one (`M4: …`), otherwise the task ID (`T03: …`).

## Sun Oct 11 — skeleton
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T00 | P0 | A | Agent guardrails: simplicity + verification rules, playbooks, Claude Code hooks, CI skip/xfail check | AGENTS.md, docs/playbooks/ | `make check` green; both hooks shown blocking | — | done |
| T01 | P0 | both | Confirm team registration on Hack2skill | — | confirmation screenshot | — | done |
| T02 | P0 | B | Public repo from this starter on branch `main`; collaborator; branch protection (checks `backend`, `web`); CODEOWNERS usernames | SETUP §3 | PR to main requires CI | — | done |
| T03 | P0 | B | `infra/setup.sh`, `firestore.sh`, `budgets.sh` (setup.sh also fills `.firebaserc`; commit it) | SETUP §4 | both DBs, bucket, SA + IAM, secrets, budgets, Firebase exist | T02 | done |
| T04 | P0 | A | Scaffold web (web/README); `make deploy-dev`; tag `v0-skeleton` + `make deploy-demo MIN_INSTANCES=0`; `make deploy-hosting` | web/README, SETUP §4 | live URL shows the shell; `/api/healthz` via Hosting answers | T03 | todo |
| T05 | P0 | A | `make smoke-live` in hi/te/ta/bn (text turn + a recorded Hindi clip); choose `LIVE_MODEL` + `LIVE_LOCATION` | infra/smoke_live.py | both checks PASS; result in STATUS.md + DECISIONS.md | T03 | todo |
| T06 | P0 | B | Meta app, test number, 5 recipients, webhook verified on dev; real secret values | SETUP §5 | Meta shows webhook verified | T04 | todo |
| T07 | P2 | B | Test sharing a WhatsApp export to the installed PWA on both phones | SPEC §4 | result in STATUS.md | T04 | todo |
| T08 | P0 | B (A helps) | Fill `seed/voice_note_script.md` from manuals; start recording | seed/voice_note_script.md | ≥15 notes recorded | — | todo |

## Mon Oct 12 — contracts (freeze 12:00), then core
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T09 | P0 | A | Pydantic models for WS frames + agent tool I/O; `/ws/live` echo stub; hand-written `seed/fixtures/live_session.jsonl` (G2 script) | contracts/ws-events.md, SPEC §6, GOLDEN_PATHS G2 | `MOCK_LIVE=1` replays G2; tests pass | T04 | todo |
| T10 | P0 | B | Pydantic models for REST + Firestore entities; stub routers returning fixtures; fixtures JSON; `make types` | contracts/rest.md, firestore.md, fault_card.schema.json | `openapi.json` + `types.ts` committed; stubs serve fixtures | T04 | todo |
| T11 | P0 | A | Live bridge (ADK `run_live`), PCM worklets, push-to-talk, captions, barge-in — Hindi end to end (M3) | SPEC §6 Live, contracts/ws-events.md | phone ↔ Ustaad in Hindi with captions on dev | T05, T09 | todo |
| T12 | P1 | A | `identify_appliance` + 6 golden photos (M2) | SPEC §6, GOLDEN_PATHS | 6/6 golden photos correct in unit test with recorded responses | T09 | todo |
| T13 | P0 | B | Ingest job: parse Android/iOS, ffmpeg, transcribe, threads (M6) | SPEC §4, contracts/firestore.md (imports) | small export fixture → messages + transcripts in test | T08, T10 | todo |
| T14 | P2 | B | Agent Search store with 3 brands' manuals (S1) | SPEC §5 | query returns a page-cited snippet | T03 | todo |

## Tue Oct 13 — features
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T15 | P0 | B | Card extraction, dedupe, 768-dim embeddings, `search_fault_cards` (M6, M2) | SPEC §4, fault_card.schema.json | demo export → ≥20 cards; search returns Ramesh's E6 card | T13 | todo |
| T16 | P0 | A | `start_repair`/`next_step`, gates + `before_tool_callback`, red screen (M5) | SAFETY.md, SPEC §6 | all SAFETY.md bypass tests fail to bypass | T11 | todo |
| T17 | P0 | A | `request_media`, camera sheet, retake loop (M4) | SPEC §6, contracts/ws-events.md | photo request → check → retake once → continue, on phone | T11 | todo |
| T18 | P1 | B | Inventory tools, `/w/stock`, voice deltas (M7) | contracts/rest.md, firestore.md | "do capacitor use kiye" → qty −2 | T10 | todo |
| T19 | P0 | B | WhatsApp webhook, quote state machine, Places search (M8) | SPEC §7 quotes, contracts/firestore.md | 3 team phones get requests; replies parsed | T06, T10 | todo |
| T20 | P2 | A | Memory Bank: preload + save (S3) | SPEC §6 Memory | 2nd session recalls language + weak area | T05 | todo |

## Wed Oct 14 — finish features, integration 21:00
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T21 | P1 | A | Onboarding interview, 4 languages (M1) | SPEC §3 M1, ws-events `profile_update` | G1 passes in hi and te | T11 | todo |
| T22 | P1 | A | `close_job` → card with photo, stock decrement (M9) | SPEC §6, firestore.md | G4 passes | T15, T18 | todo |
| T23 | P0 | B | Quotes card in job screen + approve (M8) | DESIGN.md, ws-events `quotes` | G3 passes on phone | T19 | todo |
| T24 | P1 | B | Dashboard: knowledge base, live import progress, review queue (M6) | DESIGN.md, playbooks/ui-pass.md | G5 passes on laptop | T15 | todo |
| T25 | P2 | B | Seed: 80 cards, 200 jobs, 3 workers; clusters job + area map (S2) | SPEC §10 | cluster visible, badged "Demo data" | T15 | todo |
| T26 | P0 | both | **Integration gate**: G2 + G3 on a real phone, dev | GOLDEN_PATHS | both pass; logged in STATUS.md | T15, T16, T17, T18, T19, T23 | todo |

## Thu Oct 15 — harden (freeze 18:00)
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T27 | P0 | A | Demo-safe cache, rate limits, "Try the demo" (M10) | SPEC §10 | incognito phone runs G2 with backend models slowed | T26 | todo |
| T28 | P1 | B | UI polish pass on every screen | DESIGN.md, playbooks/ui-pass.md | screenshots at 360/1280 in PR | T26 | todo |
| T29 | P1 | A | Golden tests + measure the quality bar | GOLDEN_PATHS, SPEC §10 | numbers in STATUS.md | T26 | todo |
| T30 | P0 | both | Feature freeze; tag `v1-rc`; `make deploy-demo` | WORKFLOW | demo service on v1-rc | T27–T29 | todo |

## Fri Oct 16 – Sat Oct 17 — ship
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T31 | P0 | both | Shoot video (real AC, two phones, screen capture) | PRODUCT.md | raw takes for every beat | T30 | todo |
| T32 | P0 | B | Deck (10 slides), README final, architecture image | PRODUCT.md, STATUS.md | PDF in docs/ | T29 | todo |
| T33 | P0 | A | Edit video, subtitles, narration, < 2:58 | — | uploaded unlisted + Drive copy | T31 | todo |
| T34 | P0 | A | Final demo deploy; check all links in incognito on phone and laptop | WORKFLOW checklist | checklist ticked | T33 | todo |
| T35 | P0 | both | **Submit by 21:00 IST** | WORKFLOW checklist | confirmation screenshot | T32, T34 | todo |
