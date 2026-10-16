# Fixtures (no network in unit tests)

Created on Mon Oct 12 with the contracts. Every agent and person uses these instead of live APIs.
| File | Owner | Task | Format |
| --- | --- | --- | --- |
| `live_session.jsonl` (+ `_g1`, `_te`) | A | T09 | one `{"t_ms": int, "frame": {server frame}}` per line, hand-written from GOLDEN_PATHS G2 (no audio) |
| `fault_cards.json` | B | T10 | array of FaultCard (`source.type: "synthetic"` unless from a real note) |
| `worker.json`, `vendors.json`, `quotes.json`, `close_job.json` | B | T10 | REST response shapes from `shared/contracts/rest.md` |
| `backend/fixtures/inventory.json` | B | T10 | Inventory REST response included in the backend-only Cloud Run build context |
| `identify/*.json` | A | T12 | Flash's recorded `NameplateRead` for the 6 golden photos (gemini-3.8-flash, Oct 16). Recorded on the provisional images (web/AI, kept private, never committed); re-record on our own photos. Serial-number observations are removed after recording: no unit identifiers in fixtures |
| `../whatsapp_export_small/` | B | T13 | Fully synthetic Android/iOS parser inputs; later T13 slices add generated media |

`make mock` copies the JSON/JSONL files into `web/public/mock/` for `VITE_MOCK_LIVE=1`.
Error codes and fixes in fixtures come from real manuals or recorded notes only.
