# Glossary

## Project terms
| Term | Meaning |
| --- | --- |
| Fault card | One captured fix: brand, model, code, symptom, cause, steps, parts, hazard, source (`fault_card.schema.json`) |
| Source chip | The UI tag that names where advice came from ("Ramesh · May 2025 ▶" or "Voltas manual p.12") |
| Gate | A safety check that needs photo evidence before hazardous steps unlock (`SAFETY.md`) |
| Golden path | A scripted demo flow G1–G6 that must always work (`GOLDEN_PATHS.md`) |
| Import | Turning a WhatsApp "Export chat → Include media" into fault cards (SPEC §4) |
| Quote request | One ask for a part sent to several vendors on WhatsApp; each vendor's reply becomes a quote |
| Cluster | The same model + component failing in nearby pincodes within a time window |
| Demo-safe | Mode that serves cached golden-path responses when a live call is slow or fails |
| A / B | The two workstreams (Voice & Agent / Knowledge & Commerce), WORKFLOW.md |

## Trade words workers use (keep them as spoken; don't "correct" them)
| Said | Usually means |
| --- | --- |
| mistri, mechanic, Ustaad-ji | technician; Ustaad-ji = the respected senior |
| AC paani phek raha hai / paani tapak raha hai | water leaking from the indoor unit |
| cooling nahi ho rahi | not cooling |
| gas kam hai / gas khatam | low refrigerant suspected → refrigerant work → `STOP_REFRIGERANT` |
| PCB ud gaya / board jal gaya | control board failed or burnt |
| capacitor phool gaya | capacitor swollen / failed |
| sensor kharab | a temperature sensor (thermistor) suspected faulty |
| compressor trip ho raha hai | compressor stops / protection tripping |
| MCB band karo | switch off the circuit breaker |
| voltage up-down / stabilizer | supply voltage fluctuation; stabiliser advice |
| outdoor / indoor unit | the two halves of a split AC |
| 1 ton, 1.5 ton, inverter, non-inverter | capacity and compressor type |
| ho gaya / theek ho gaya | done / fixed (triggers job close) |

Error codes are brand- and model-specific. Their meanings come only from the brand's manual or the team's recorded
notes, never from general knowledge.
