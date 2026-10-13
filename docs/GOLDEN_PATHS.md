# Golden paths (the demo; tested before every demo deploy)

Each path has exact inputs and the frames/results that must appear. Unit tests use recorded fixtures; golden
tests (`make golden`) run the same script against real models. The video is these paths, in this order.

| ID | Language | Inputs | Must see | Fixture |
| --- | --- | --- | --- | --- |
| G1 Onboard | hi (and te) | language tile → answers: "AC aur fridge", "Voltas, LG, Daikin", "201301", "8 saal", "capacitor, PCB nahi", "Sharma Electricals" | `profile_update` frames fill trades, brands, pincode, experience, stock, vendors; worker saved with `onboarding_done` | `live_session_g1.jsonl` |
| G2 Stuck | hi | golden photo `nameplate_voltas.jpg` + `display_e6.jpg`; "E6 aa raha hai, kya karun?" | `identified` (brand, model, code from the real manual) → `step_card` with source chip "Ramesh · <date>" that plays audio → `media_request` for the outdoor PCB → blurry photo → `media_result` with retake reason → clear photo → `safety_gate G_MAINS_OFF` → MCB photo → `gate_result passed` → next `step_card` | `live_session.jsonl` |
| G3 Part | hi | "PCB nahi hai" | `tool_activity` "stock check" → `stock` qty 0 → `quotes` updated 3 times as team phones reply (one by voice note) → approve → confirmation messages sent | `quotes.json` |
| G4 Close | hi | "Ho gaya, capacitor badla" | `job_closed` with a new card id; card has `photo_uri`; stock for capacitor −1 | `close_job.json` |
| G5 Import | — | `seed/whatsapp_export/` demo zip on `/d/import` | progress counts rise; ≥ 20 cards appear live with speaker, date, playable audio; low-confidence cards in review queue | `whatsapp_export_small/` (unit) |
| G6 Telugu | te | same as G2's first question in Telugu | answers in Telugu speech; captions in Telugu script; same source card | `live_session_te.jsonl` |
| G7 Side issue (optional, only if T36 done by Thu 18:00) | hi | mid-step: "yahan wire bhi jala hua lag raha hai" → photo of the wire → "baad mein" | `media_request` → photo → `media_result` → worker "baad mein" → the same `step_card` re-sent | — |
| G8 General guidance (optional, only if T39 done by Thu 18:00; mock fixture only, never run against real models) | hi | a washing-machine symptom that no card or manual matches | Ustaad's caption says this is general guidance with no verified source → `safety_gate G_MAINS_OFF` → photo of the plug removed → `gate_result passed` → `step_card` with `source.kind: "general"`, its chip reading "General guidance" with no audio button | `live_session_general.jsonl` (T39) |

Error-code meanings and fixes in every fixture must come from the real manuals or the team's recorded notes
(seed/voice_note_script.md). Never invent them. The one exception is G8: its step is a general check the worker can
prove with a photo, is labelled general, and states no error-code meaning, component value or wiring.
