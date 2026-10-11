# Fixtures (no network in unit tests)

Created on Mon Oct 12 with the contracts. Every agent and person uses these instead of live APIs.
| File | Owner | Task | Format |
| --- | --- | --- | --- |
| `live_session.jsonl` (+ `_g1`, `_te`) | A | T09 | one `{"t_ms": int, "frame": {server frame}}` per line, hand-written from GOLDEN_PATHS G2 (no audio) |
| `fault_cards.json` | B | T10 | array of FaultCard (`source.type: "synthetic"` unless from a real note) |
| `worker.json`, `inventory.json`, `vendors.json`, `quotes.json`, `close_job.json` | B | T10 | REST response shapes from `shared/contracts/rest.md` |
| `whatsapp_export_small/` | B | T13 | 1 chat txt (Android format) + 1 short consented voice note + 1 photo |

`make mock` copies the JSON/JSONL files into `web/public/mock/` for `VITE_MOCK_LIVE=1`.
Error codes and fixes in fixtures come from real manuals or recorded notes only.
