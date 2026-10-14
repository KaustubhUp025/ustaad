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
| T04 | P0 | A | Scaffold web (web/README); `make deploy-dev`; tag `v0-skeleton` + `make deploy-demo MIN_INSTANCES=0`; `make deploy-hosting` | web/README, SETUP §4 | live URL shows the shell; `/api/healthz` via Hosting answers | T03 | done |
| T05 | P0 | A | `make smoke-live` in hi/te/ta/bn (text turn + a recorded Hindi clip); choose `LIVE_MODEL` + `LIVE_LOCATION` | infra/smoke_live.py | both checks PASS; result in STATUS.md + DECISIONS.md | T03 | done |
| T06 | P0 | B | Meta app, test number, 5 recipients, webhook verified on dev; real secret values | SETUP §5 | Meta shows webhook verified | T04 | todo |
| T07 | P2 | B | Test sharing a WhatsApp export to the installed PWA on both phones | SPEC §4 | result in STATUS.md | T04 | todo |
| T08 | P0 | B (A helps) | Fill `seed/voice_note_script.md` from manuals; start recording | seed/voice_note_script.md | ≥15 notes recorded | — | todo |

## Mon Oct 12 — contracts (freeze 12:00), then core
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T09 | P0 | A | Pydantic models for WS frames + photo-tool I/O (other tools' I/O with their own tasks); `/ws/live` echo stub; hand-written `seed/fixtures/live_session.jsonl` (G2 script) | contracts/ws-events.md, SPEC §6, GOLDEN_PATHS G2 | `MOCK_LIVE=1` replays G2; tests pass | T04 | done |
| T10 | P0 | B | Pydantic models for REST + Firestore entities; stub routers returning fixtures; fixtures JSON; `make types` | contracts/rest.md, firestore.md, fault_card.schema.json | `openapi.json` + `types.ts` committed; stubs serve fixtures | T04 | doing |
| T11 | P0 | A | Live bridge (ADK `run_live`), PCM worklets, push-to-talk, captions, barge-in — Hindi end to end (M3) | SPEC §6 Live, contracts/ws-events.md | phone ↔ Ustaad in Hindi with captions on dev | T05, T09 | done |
| T12 | P1 | A | `identify_appliance` + 6 golden photos (M2); `type` normalised to the `appliance_type` values, and the one mapping constant from a `trades` value to card types (T38) | SPEC §6, GOLDEN_PATHS | 6/6 golden photos correct in unit test with recorded responses; normalisation and mapping tests | T09 | todo |
| T13 | P0 | B | Ingest job: parse Android/iOS, ffmpeg, transcribe, threads (M6) | SPEC §4, contracts/firestore.md (imports) | small export fixture → messages + transcripts in test | T08, T10 | todo |
| T14 | P2 | B | Agent Search store with 3 brands' manuals (S1) | SPEC §5 | query returns a page-cited snippet | T03 | todo |

## Tue Oct 13 — features
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T15 | P0 | B | Card extraction, dedupe, 768-dim embeddings, `search_fault_cards` (M6, M2) | SPEC §4, fault_card.schema.json | demo export → ≥20 cards; search returns Ramesh's E6 card | T13 | todo |
| T16 | P0 | A | `start_repair`/`next_step`, gates + `before_tool_callback`, red screen (M5); hazard tagger and rules table, default gate for unsourced jobs, stop reasons, general steps through `start_repair` (T38) | SAFETY.md, SPEC §6 | all SAFETY.md bypass tests fail to bypass; SAFETY.md general-tier tests pass, except the caption backstop (T39) | T11 | done |
| T17 | P0 | A | `request_media`, camera sheet, retake loop (M4); from T16: the gate screen's photo button opens the camera sheet, and `confirm_safety` accepts only a `media_uri` from a server-issued request in `jobs.media` | SPEC §6, contracts/ws-events.md | photo request → check → retake once → continue, on phone | T11 | todo |
| T18 | P1 | B | Inventory tools, `/w/stock`, voice deltas (M7) | contracts/rest.md, firestore.md | "do capacitor use kiye" → qty −2 | T10 | todo |
| T19 | P0 | B | WhatsApp webhook, quote state machine, Places search (M8) | SPEC §7 quotes, contracts/firestore.md | 3 team phones get requests; replies parsed | T06, T10 | todo |
| T20 | P2 | A | Memory Bank: preload + save (S3) | SPEC §6 Memory | 2nd session recalls language + weak area | T05 | todo |

## Wed Oct 14 — finish features, integration 21:00
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T21 | P1 | A | Onboarding interview, 5 languages: hi, te, ta, bn, en (M1); `trades` limited to 3 listed values, validated in `save_profile_fields`, shown as chips (T38) | SPEC §3 M1, ws-events `profile_update`, firestore.md `workers` | G1 passes in hi and te; profile tests: 4 values rejected, 3 accepted, unknown value rejected, duplicates rejected; naming 4 appliances leads to a "pick your top 3" turn | T11 | todo |
| T22 | P1 | A | `close_job` → card with photo, stock decrement (M9) | SPEC §6, firestore.md | G4 passes | T15, T18 | todo |
| T23 | P0 | B | Quotes card in job screen + approve (M8) | DESIGN.md, ws-events `quotes` | G3 passes on phone | T19 | todo |
| T24 | P1 | B | Dashboard: knowledge base, live import progress, review queue (M6) | DESIGN.md, playbooks/ui-pass.md | G5 passes on laptop | T15 | todo |
| T25 | P2 | B | Seed: 80 cards, 200 jobs, 3 workers; clusters job + area map (S2) | SPEC §10 | cluster visible, badged "Demo data" | T15 | todo |
| T26 | P0 | both | **Integration gate**: G2 + G3 on a real phone, dev | GOLDEN_PATHS | both pass; logged in STATUS.md | T15, T16, T17, T18, T19, T23 | todo |
| T36 | P2 | A | Side issues mid-repair: instruction paragraph, `park_repair` / `resume_repair`, `media[].reason`, close-job question (S7) | BUILD-GUIDE §9, SPEC §6, SAFETY.md | tests in BUILD-GUIDE §9.7 (A) pass; on phone: side photo mid-step → choose "baad mein" → same step resumes | T16, T17 | todo |
| T37 | P2 | A | Manual / sticker photo: `kind:"document"`, ManualPage extraction, `manual_photo` source chip, "Manual photo" button (S7) | BUILD-GUIDE §9, contracts/ws-events.md | tests in BUILD-GUIDE §9.7 (B) pass; real photographed page cited on phone | T17, contracts PR merged | todo |

## General-appliance tier (T38 onward; before the freeze, and only after M2–M5, M6 and M8 work for AC)
Lane A's code is folded into T12, T16 and T21 above. These rows are the rest. First in the cut order (SPEC §3).
| ID | P | Owner | Task | Read | Done when | Out of scope | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T38 | P2 | A | Contracts and docs for the general-appliance tier | SPEC §6, SAFETY.md, shared/contracts/ | contracts PR #15 merged; SPEC, SAFETY, TASKS and GOLDEN_PATHS updated | any code | — | done |
| T39 | P2 | A | Source tiers in `instruction.md` (text proposed, A approves); caption backstop (from T16: run it on the worker's final captions too, so a gas question gets the stop screen); "General guidance" source chip with no audio button; stop-screen text per reason in all five i18n files | BUILD-GUIDE `#### T39`, SPEC §6 (source tiers), SAFETY.md, DESIGN.md, ws-events `step_card` and `safety_stop` | a final Ustaad caption matching a stop row sends `safety_stop`; the chip renders for `source.kind: general`; G8 replays from its mock fixture; manual check written into STATUS.md: 5 out-of-card questions in Hindi (washing machine, fridge, LED TV, geyser, microwave), each answer labelled general, no invented error-code meaning, asks to see before guessing | web search; video; any extra model call; audio on stop screens | T16, T21 | todo |
| T40 | P2 | B | Card extraction prompt sets `appliance_type`; an unclear type goes to the review queue | BUILD-GUIDE `#### T40`, SPEC §4, fault_card.schema.json | extraction test: a non-AC thread gets its type; an unclear one gets `review_status: needs_review` | backfilling existing cards; manual metadata in Agent Search | T15 | todo |
| T41 | P2 | B | `search_fault_cards`: optional `appliance_type` filter in code after the vector query (fetch the top 20, drop other types); empty list when the best match is below a named relevance-floor constant (a marked placeholder until it is set from real embeddings) | BUILD-GUIDE `#### T41`, SPEC §6, contracts/rest.md | an "LG TV" query never returns AC cards; an unrelated symptom returns an empty list; the Voltas query still returns Ramesh's card | a new Firestore index; manual metadata in Agent Search | T15 | todo |

## Thu Oct 15 — harden (freeze 18:00)
| ID | P | Owner | Task | Read | Done when | Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T27 | P0 | A | Demo-safe cache, rate limits, "Try the demo" (M10); T11 follow-ups: close silent sockets after 45 s, mic usable while reconnecting (BUILD-GUIDE T27) | SPEC §10 | incognito phone runs G2 with backend models slowed; silent socket closed and its Live slot freed | T26 | todo |
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

T10 progress: inventory contracts, strict models and synthetic offline fixtures/tests only.
Inventory approval is scoped to this slice. Routes, lookup, persistence, negative-stock
enforcement and T18 voice-boundary normalization remain pending; no update_inventory wrapper exists.
Other T10 entities/stubs remain pending. Inventory is not exposed in OpenAPI until a route references it.
T10 aligned with T38 docs on main (`3c163eb`): inventory rules unchanged; remaining Worker,
Job and FaultCard models must use the general-appliance constraints noted in BUILD-GUIDE T10.
T10 coordination: merged PR #19 owns the shared repair types. The complete public FaultCard now imports
`Hazard` and `ApplianceType`; its fixture and offline validation tests are present. Job remains pending and
must import the shared step/gate types. Job validation/loading must preserve stored gate states, while the
later creation flow starts new jobs with gates open.
