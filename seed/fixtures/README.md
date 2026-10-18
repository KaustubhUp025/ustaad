# Fixtures (no network in unit tests)

Created on Mon Oct 12 with the contracts. Every agent and person uses these instead of live APIs.
| File | Owner | Task | Format |
| --- | --- | --- | --- |
| `live_session.jsonl` (+ `_g1`, `_te`) | A | T09 | one `{"t_ms": int, "frame": {server frame}}` per line, hand-written from GOLDEN_PATHS G2 (no audio) |
| `live_session_general.jsonl` | A | T39 | same format, hand-written from GOLDEN_PATHS G8 (mock only); its one step is the single general step allowed in fixtures (AGENTS.md). Replayed at `/w/job/general` |
| `live_session_g1.jsonl`, `live_session_g1_te.jsonl` | A | T21 | Same format. G1 onboarding in hi and te, recorded Oct 18 from the real Live model (LIVE_MODEL) with the six G1 answers sent as text turns and in-memory stores; partial captions dropped, the worker's turns written as `who: user` captions |
| `fault_cards.json` | B | T10 | array of FaultCard (`source.type: "synthetic"` unless from a real note) |
| `worker.json` | A | T27 | The seeded demo worker `w_hi_demo` (Worker shape, `demo: true`); seeds `workers/w_hi_demo` for "Try the demo" |
| `vendors.json`, `quotes.json`, `close_job.json` | B | T10 | REST response shapes from `shared/contracts/rest.md` |
| `backend/fixtures/inventory.json` | B | T10 | Inventory REST response included in the backend-only Cloud Run build context |
| `identify/*.json` | A | T12 | Flash's recorded `NameplateRead` for the 6 golden photos (gemini-3.8-flash, Oct 16). Recorded on the provisional images (web/AI, kept private, never committed). Plus 5 recorded on our own photos (Oct 18, metadata-free copies, kept private): `nameplate_voltas_window`, `nameplate_marq_split`, `nameplate_marq_hard`, `nameplate_voltas_beko_washer`, `display_lg_window`. Serial-number observations are removed after recording: no unit identifiers in fixtures |
| `manual_pages.json` | A | T37 | `ManualPage` answers for manual-page photos. `voltas_error_table` and `blurry`: recorded from Flash (FLASH_MODEL, Oct 17) on the Voltas manual's printed p.30, rendered from the PDF named in `seed/manual_codes.json` (sha256 85bc5032…), clear and at 22 dpi; all 33 codes match the hand-verified table. `daikin_*`: transcribed verbatim from the verified Daikin SiUS091133 lines there (safety lines, CH61 first check) |
| `agent_search/voltas_e6.json` | A | T14 | A `SearchResponse` recorded Oct 18 from `ustaad-manuals-layout` (chunk mode) for "Voltas E6"; kept in a subfolder so `make mock` doesn't copy it |
| `../whatsapp_export_small/` | B | T13 | Fully synthetic Android/iOS parser inputs; later T13 slices add generated media |

`make mock` copies the JSON/JSONL files into `web/public/mock/` for `VITE_MOCK_LIVE=1`.
Error codes and fixes in fixtures come from real manuals or recorded notes only.
