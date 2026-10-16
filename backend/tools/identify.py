"""identify_appliance's rules (SPEC §6, BUILD-GUIDE T12): the vision reading with the brand spelled as on the cards,
the code as shown on the display and the type as one of the `appliance_type` values. Pure: the vision call is the caller's. A code's meaning is never
given here; it comes from search."""

import re
from typing import get_args

from models.repair import ApplianceType
from models.tools import IdentifyOut, NameplateRead
from tools.search_fault_cards import canonical_brand

# First match wins, so the more specific words come first ("window AC" before "AC", "air cooler" before "air").
TYPE_WORDS: list[tuple[ApplianceType, list[set[str]]]] = [
    ("window_ac", [{"window"}]),
    ("washing_machine", [{"washing"}, {"washer"}]),
    ("fridge", [{"fridge"}, {"refrigerator"}]),
    ("led_tv", [{"tv"}, {"television"}]),
    ("microwave", [{"microwave"}, {"oven"}]),
    ("geyser", [{"geyser"}, {"water", "heater"}]),
    ("fan_cooler", [{"cooler"}, {"fan"}]),
    ("split_ac", [{"split"}, {"ac"}, {"air", "conditioner"}]),
]


def normalise_type(said: str | None) -> ApplianceType | None:
    if said is None:
        return None
    if said in get_args(ApplianceType):
        return said
    words = set(re.findall(r"[a-z]+", said.lower()))
    return next((value for value, groups in TYPE_WORDS if any(g <= words for g in groups)), "other")


def normalise_code(shown: str | None) -> str | None:
    return re.sub(r"\s+", "", shown or "").upper() or None


def identify(read: NameplateRead) -> IdentifyOut:
    return IdentifyOut(
        # Spelled as the cards spell it, so the job's brand finds them.
        brand=read.brand and canonical_brand(read.brand),
        model=read.model,
        series=read.series,
        type=normalise_type(read.type),
        error_code=normalise_code(read.error_code),
        confidence=read.confidence,
        observations=read.observations,
    )
