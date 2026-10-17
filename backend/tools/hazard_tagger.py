"""Hazard tagger (docs/SAFETY.md): reads a step's one-line English summary against one rules table and gives the
step's hazard, raised but never lowered, or the hard stop it hits. Plain text in, so the import pipeline can call
it on card steps later."""

import re
from typing import get_args

from models.repair import Hazard, StopReason

# One row per outcome: a stop reason or a hazard level, and the keyword groups that match it. A group matches when
# all its words are in the summary. Stop rows come first: a stop wins over any hazard level.
RULES: list[tuple[StopReason | Hazard, list[set[str]]]] = [
    (
        "refrigerant",
        [{"refrigerant"}, {"gas"}, {"recharge"}, {"recharging"}, {"brazing"}, {"braze"}, {"nitrogen"}, {"manifold"}],
    ),
    (
        "microwave_hv",
        [
            {"magnetron"},
            {"microwave", "capacitor"},
            {"microwave", "transformer"},
            {"microwave", "diode"},
            {"microwave", "cover"},
            {"microwave", "cabinet"},
            {"microwave", "inside"},
        ],
    ),
    ("crt", [{"crt"}, {"picture", "tube"}, {"flyback"}, {"cathode"}, {"anode"}]),
    (
        "geyser_open",
        [{"geyser", word} for word in ("open", "inside", "cover", "panel", "lid", "tank", "element", "thermostat")],
    ),
    ("capacitor", [{"capacitor"}]),
    (
        "HV",
        [
            {word}
            for word in (
                "pcb", "board", "terminal", "wiring", "wire", "mains", "live", "socket", "connector", "relay",
                "fuse", "compressor", "motor", "transformer", "element", "thermostat", "voltage",
            )
        ],
    ),
]
LEVELS: list[Hazard] = ["none", "HV", "capacitor"]
# General steps never need the power on (SAFETY.md). Kept out of RULES: card and manual steps may need it, and the
# speech backstop must not stop the power-on diagnosis that happens in conversation before start_repair.
POWER_ON: list[set[str]] = [
    {"voltage"}, {"volt"}, {"supply"}, {"live"}, {"tester"}, {"energised"}, {"energized"},
    {"power", "on"}, {"switch", "on"}, {"turn", "on"},
]


def _words(text: str) -> set[str]:
    # Plurals count as the singular ("terminals" matches "terminal"); short words like "gas" are left alone.
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text.lower())}


def tag(summary_en: str, hazard: Hazard) -> tuple[Hazard, StopReason | None]:
    """The step's hazard after tagging and the stop reason it hits, if any. A `refrigerant` hazard is a stop."""
    if hazard == "refrigerant":
        return hazard, "refrigerant"
    words = _words(summary_en)
    matched = [outcome for outcome, groups in RULES if any(group <= words for group in groups)]
    stop = next((m for m in matched if m in get_args(StopReason)), None)
    if stop:
        return hazard, stop
    return max([hazard, *matched], key=LEVELS.index), None


def needs_power_on(summary_en: str) -> bool:
    words = _words(summary_en)
    return any(group <= words for group in POWER_ON)
