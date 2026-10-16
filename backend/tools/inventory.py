"""Inventory rules (BUILD-GUIDE T18): find a part by what he called it, apply stock deltas all or nothing, and flag low
stock. A part that is unknown or unclear is an error, never a new part; stock never goes below zero. Pure: the
Firestore transaction is the caller's."""

import math
import re
from datetime import datetime
from typing import Literal

from models.inventory import InventoryDelta, InventoryItem
from models.tools import StockErrorReason, StockLine


class StockError(Exception):
    def __init__(self, reason: StockErrorReason, part: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.part = part


def _key(text: str) -> str:
    # "Capacitor 2.5 mfd", "capacitor 2.5µF" and "Capacitor 2.5uF" are the same part.
    text = text.lower().replace("µ", "u").replace("mfd", "uf")
    return re.sub(r"[^a-z0-9.]", "", text)


def _head(text: str) -> str:
    words = text.lower().split()
    return _key(words[-1]) if words else ""


def find(items: list[InventoryItem], said: str) -> list[InventoryItem]:
    """Every part `said` could mean: an exact name or alias first, then a category, then a name or alias that ends in
    the same word ("tape" -> "Insulation tape"). A word in the middle never matches: "compressor" is not a
    "compressor capacitor"."""
    k = _key(said)
    names = {i.id: [_key(n) for n in (i.name, *i.aliases)] for i in items}
    head = _head(said)
    tiers = [
        [i for i in items if k in names[i.id]],
        [i for i in items if i.category and _key(i.category) == k],
        [i for i in items if head and head in (_head(n) for n in (i.name, *i.aliases))],
    ]
    return next((tier for tier in tiers if tier), [])


def apply_deltas(
    items: list[InventoryItem],
    deltas: list[InventoryDelta],
    source: Literal["voice", "manual"],
    now: datetime,
) -> list[InventoryItem]:
    """The changed parts, in the order first named. Raises StockError and changes nothing if any delta fails."""
    totals: dict[str, int] = {}
    for d in deltas:
        found = find(items, d.part)
        if len(found) != 1:
            raise StockError("unknown_part" if not found else "ambiguous_part", d.part)
        totals[found[0].id] = totals.get(found[0].id, 0) + d.delta
    by_id = {i.id: i for i in items}
    changed = []
    for pid, total in totals.items():
        qty = by_id[pid].qty + total
        if qty < 0:
            raise StockError("below_zero", by_id[pid].name)
        changed.append(by_id[pid].model_copy(update={"qty": qty, "source": source, "updated_at": now}))
    return changed


def is_low(item: InventoryItem) -> bool:
    return item.qty <= item.min_qty


def stock_line(item: InventoryItem) -> StockLine:
    return StockLine(part=item.name, qty=item.qty, min_qty=item.min_qty, low=is_low(item))


def voice_delta(value: object) -> int:
    """The Live model may send 2.0 for 2 (rest.md, voice compatibility): whole numbers only, never zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("delta must be a number")  # noqa: TRY004 — one rejection for every bad delta (rest.md)
    if not math.isfinite(value) or value != int(value) or value == 0:
        raise ValueError("delta must be a nonzero whole number")
    return int(value)
