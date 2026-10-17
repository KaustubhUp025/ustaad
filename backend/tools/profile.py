"""Onboarding answers (BUILD-GUIDE T21, G1): each answer is checked and applied on its own, so one bad answer never
loses the others. Trades are 1 to 3 listed values (more asks for his top 3, never cut silently), the pincode is 6
digits, brands get one spelling. Pure: loading, saving and the frame are the caller's."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import get_close_matches
from typing import Any, get_args
from uuid import uuid4

from models.inventory import InventoryItem
from models.repair import Trade
from models.worker import Lang, ProfileProblem, SaveProfileIn, SaveProfileOut, Worker
from tools.inventory import find
from tools.search_fault_cards import canonical_brand

MAX_TRADES = 3
MAX_YEARS = 60
PINCODE = re.compile(r"[1-9]\d{5}")
# Common brands in Indian AC and appliance repair, so a misheard name ("Voltaas") gets its usual spelling.
BRANDS = [
    "Voltas", "LG", "Daikin", "Samsung", "Whirlpool", "Godrej", "Blue Star", "Hitachi", "Carrier", "Panasonic",
    "Lloyd", "Haier", "IFB", "Bosch", "Onida", "Videocon", "Mitsubishi", "O General", "Toshiba", "Sony", "Bajaj",
    "Havells", "Crompton", "Kelvinator", "Sharp", "Croma", "Midea", "AO Smith", "Racold", "Usha", "Orient",
]
BRAND_MATCH = 0.8


@dataclass
class ProfileChange:
    out: SaveProfileOut
    worker: Worker
    # What the profile card shows for this call (the `profile_update` frame's fields).
    shown: dict[str, Any]
    new_parts: list[InventoryItem] = field(default_factory=list)
    shop: str | None = None


def fresh_worker(worker_id: str, lang: Lang, now: datetime) -> Worker:
    return Worker(
        id=worker_id, name="", lang=lang, trades=[], brands=[], pincode=None, geo=None, experience_yrs=None,
        onboarding_done=False, skill_gaps=[], demo=True, created_at=now,
    )


def _brand(said: str) -> str:
    spelled = canonical_brand(said.strip())
    match = get_close_matches(spelled.lower(), [b.lower() for b in BRANDS], n=1, cutoff=BRAND_MATCH)
    return next(b for b in BRANDS if b.lower() == match[0]) if match else spelled


def _trades_problem(trades: list[str]) -> str | None:
    if len(trades) > MAX_TRADES:
        return "pick_top_3"
    if any(t not in get_args(Trade) for t in trades):
        return "unknown_trade"
    if len(set(trades)) != len(trades):
        return "duplicate_trade"
    return None


def _stock(answers, items: list[InventoryItem], now: datetime) -> list[InventoryItem]:
    """Parts he gave a count for: his existing part gets the count, any other becomes a new part."""
    parts = []
    for answer in answers:
        if not answer.qty:
            continue
        known = find(items, answer.part)
        if len(known) == 1:
            parts.append(known[0].model_copy(update={"qty": answer.qty, "source": "voice", "updated_at": now}))
        else:
            parts.append(
                InventoryItem(
                    id=f"part_{uuid4().hex[:8]}", name=answer.part, category=None, aliases=[], qty=answer.qty,
                    min_qty=1, unit_cost_inr=None, source="voice", updated_at=now,
                )
            )
    return parts


def save_profile(inp: SaveProfileIn, worker: Worker, items: list[InventoryItem], now: datetime) -> ProfileChange:
    problems: list[ProfileProblem] = []
    update: dict[str, Any] = {}
    shown: dict[str, Any] = {}
    if inp.trades is not None:
        reason = _trades_problem(inp.trades)
        if reason:
            problems.append(ProfileProblem(field="trades", reason=reason))
        else:
            update["trades"] = shown["trades"] = inp.trades
    if inp.brands is not None:
        update["brands"] = shown["brands"] = list(dict.fromkeys(_brand(b) for b in inp.brands if b.strip()))
    if inp.pincode is not None:
        digits = re.sub(r"\s", "", inp.pincode)
        if PINCODE.fullmatch(digits):
            update["pincode"] = shown["pincode"] = digits
        else:
            problems.append(ProfileProblem(field="pincode", reason="not_6_digits"))
    if inp.experience_yrs is not None:
        if 0 <= inp.experience_yrs <= MAX_YEARS:
            update["experience_yrs"] = shown["experience_yrs"] = inp.experience_yrs
        else:
            problems.append(ProfileProblem(field="experience_yrs", reason="not_plausible"))
    new_parts = _stock(inp.stock or [], items, now)
    if inp.stock is not None:
        shown["stock"] = [a.model_dump() for a in inp.stock]
    shop = (inp.shop or "").strip() or None
    if shop:
        shown["shop"] = shop
    worker = worker.model_copy(update=update)
    if inp.done:
        if worker.trades:
            worker = worker.model_copy(update={"onboarding_done": True})
        else:
            problems.append(ProfileProblem(field="trades", reason="missing"))
    out = SaveProfileOut(
        status="ASK_AGAIN" if problems else "SAVED", problems=problems, onboarding_done=worker.onboarding_done
    )
    return ProfileChange(out=out, worker=worker, shown=shown, new_parts=new_parts, shop=shop)
