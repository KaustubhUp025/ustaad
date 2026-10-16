# Gold set for the card import (BUILD-GUIDE §8.8)

Written on Oct 16 from `seed/voice_note_script.md`, **before** the import ran on the export, so the accuracy number is
honest. One row per chat. Facts come from the script, which follows the manuals (`seed/manual_codes.json`).

**How to score a run.** Match each produced card to a row by its `message_ids`. A card is **correct** when brand, code,
cause and fix match the row and its hazard is not lower than "Min hazard". A card with no matching row is wrong.
Precision = correct / produced cards; recall = rows expecting a card that got a correct one / rows expecting a card.
Record both, with the date and model, in `docs/STATUS.md`. The bar is ≥ 20 cards and ≥ 80% correct (SPEC §10).

**Brand.** The importer sees only the messages, not the script's headings. When no message names the brand or shows it,
the row's brand is "" (a general card, offered for every brand). Guessing a brand that isn't in the thread scores wrong.

**Credit** is whoever states the fix: from the recording log when recorded, otherwise the plan ("plan"). Update it
from the export before scoring.

| Chat | Expected | Brand | Code | Type | Cause | Fix (gist) | Min hazard | Credit |
|---|---|---|---|---|---|---|---|---|
| 1 | card ⭐ G2; the first take and the retake **merge** (verified_count 2) and the card keeps Samyak's voice note | Voltas | E6 | split_ac | indoor–outdoor communication fault; loose communication wire | MCB off, wait 5 min, check the communication wire at both terminals | HV | Samyak (voice, PTT-20261016-WA0029) |
| 2 | card | Daikin | U4 | split_ac | indoor–outdoor signal transmission error; wire 3 broken | power off and wait 10 min; check the connection wire, especially wire 3 | HV | Samyak |
| 3 | card | Voltas | "" | split_ac | drain pipe joint came off | power off; refit and tape the drain pipe joint | none | Samyak |
| 4 | no card (unanswered) | | | | | | | |
| 5 | card | LG | "" | split_ac | swollen capacitor; outdoor fan not turning, compressor humming | MCB off, discharge with an insulated tool, meter under 5 V, replace with the same µF and voltage rating | capacitor | Somil |
| 6 | card | LG | CH05 | split_ac | indoor–outdoor communication error; can follow supply fluctuation | breaker off for 5 min, then on; if it stays, call service | none | Samyak (plan) |
| 7 | card | "" | "" | split_ac or null | remote cells dead | check the cells, then obstruction, then re-plug | none | Samyak (text) |
| 8 | no card (off-topic) | | | | | | | |
| 9 | card | LG | OE | washing_machine | not draining; coin in the drain filter | unplug; check the drain hose for kinks; clean the drain filter | none | Somil (plan) |
| 10 | card, **refrigerant** (STOP_REFER when used) | "" | "" | split_ac or null | refrigerant leak (oil stain on the pipe) | no self-refill: leak fixed and gas charged only by a certified gas technician | refrigerant | Samyak |
| 11 | card | Voltas | P7 | split_ac | indoor coil anti-freeze protection; dirty filter | read the code with ADJ (8 presses in 10 s); power off, wash the filter, check the airflow | none | Samyak (plan) |
| 12 | card | LG | "" | split_ac | mounting plate not level | level the plate; drain pipe must not bend upward | none | Somil (plan) |
| 13 | card | Voltas | P8 | split_ac | outdoor coil overheating; airflow blocked | MCB off; clear the area around the outdoor unit; clean the coil | none | Samyak (plan) |
| 14 | card | Voltas | P3 | split_ac | supply voltage protection; voltage dropping to 180 V | check the supply and MCB rating; install a stabiliser | HV | Samyak (plan) |
| 15 | card | "" | IE | washing_machine | no water coming in; tap half closed | open the tap fully; check the hose for kinks; check the inlet filter | none | Somil (plan) |
| 16 | card; **Samyak's** fix, not Somil's "replace the PCB" (a card whose steps replace the board scores wrong); review status either | Voltas | F9 | split_ac | outdoor DC fan fault; leaf stuck, connector loose | MCB off, wait 5 min; turn the fan by hand, clear it; check the connector; board later | HV | Samyak (plan) |
| 17 | card | "" | "" | split_ac or null | dirty filter, fan on low | check the setting, filter, fan speed, doors and windows before suspecting gas | none | Samyak (plan) |
| 18 | **needs_review** (unsure answer, unsure outcome) | "" | "" | split_ac or null | maybe capacitor or motor | (changed the capacitor; unsure) | capacitor | Somil (plan) |
| 19 | card | Voltas | E4 | split_ac | room sensor faulty or its connector loose | MCB off, wait 5 min; check the room sensor connector on the indoor board | HV | Samyak (plan) |
| 20 | card | Daikin | A5 | split_ac | freeze-up protection; air filter clogged | power off before removing the filter; clear the airflow, filter and coil dust | none | Samyak (plan) |
| 21 | card | "" | "" | split_ac or null | MCB tripped | check power, the plug, the MCB and the timer | none | Samyak (plan) |
| 22 | card | LG | CH61 | split_ac | outdoor unit overheating; no space around it | make room around the outdoor unit; remove obstructions | none | Samyak (plan) |
| 23 | card | "" | UE | washing_machine | load unbalanced (one blanket alone) | add 2–3 items or spread the load | none | Somil (plan) |
| 24 | card | Daikin | L5 | split_ac | output overcurrent; a connector reversed during a part change | power cycle once; power off and wait 10 min; check the wiring touched yesterday | HV | Samyak (plan) |
| 25 | **merge into 19** (the chat-19 card gets verified_count 2; no new card) | Voltas | E4 | split_ac | as 19 | as 19 | HV | (19's credit stays) |
| 26 | **needs_review** (appliance unclear) | "" | "" | null | loose plug | check the plug and socket supply | none | Kaustubh (plan) |
| 27 | card | "" | "" | split_ac or null | room smell collects in the filter | wash the filter; else a service | none | Samyak (plan) |

**Totals expected:** 22 cards (chats 1–3, 5–7, 9–17, 19–24, 27), plus 2 in review (18, 26); chat 25 merges into 19;
chats 4 and 8 give nothing. Codes are copied as shown; their meanings above are the manuals' (see `seed/manual_codes.json`).
