"""Import step 7 (BUILD-GUIDE T15): one Flash card draft per thread, turned into a FaultCard by code (credit, hazard,
review), embedded, deduped against the brand's cards and written."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from jobs.ingest.dedupe import LEVELS, match, merge
from models.fault_card import FaultCard, FaultCardSource
from models.imports import CardCounts, CardDraft, ThreadMessage
from tools.hazard_tagger import tag
from tools.search_fault_cards import Embed, canonical_brand

Ask = Callable[[str, type[CardDraft]], Awaitable[CardDraft]]
logger = logging.getLogger(__name__)

REVIEW_CONFIDENCE = 0.6
EXTRACT_PARALLEL = 8
MATCH_CANDIDATES = 5
# WhatsApp exports carry no timezone; the group is in India (BUILD-GUIDE §12 risk 14).
EXPORT_TZ = ZoneInfo("Asia/Kolkata")
# Goes to imports.errors[] and the dashboard, so it is fixed text: never exception text, ids, URIs or chat content.
EXTRACTION_FAILED = "One chat thread could not be read, so it was skipped."

PROMPT = """ROLE: You turn a technician chat thread into one fault card draft.
RULES: 1 A card exists only if a fix or conclusion is stated. Unanswered questions -> resolved false.
       2 Use only what people said or what photos show. Never add an error-code meaning, step or part not in the thread.
       3 fix_message_id: the id of the answer that gives the fix or diagnosis, not the asker's report that it
         worked; that report is only the outcome. message_ids: every message id you used.
       4 Each step: text as said, summary_en (one line of English), hazard none | HV | capacitor | refrigerant.
         Anything with gas charging, leak repair, brazing or pressure work is refrigerant. Anything touching a
         capacitor is capacitor. Anything touching wiring, terminals, the PCB or mains is HV.
       5 confidence 0-1: low if the speaker was unsure, the audio unclear, or people disagreed.
       6 error_code verbatim as shown on the unit, or null. Keep Hinglish, codes and part numbers verbatim.
       7 language: BCP-47 of the steps' text, e.g. hi-Latn for romanised Hinglish.
       8 brand: as said or shown in the thread, else null; never guess the brand from the code or other threads.
       9 appliance_type: one of the allowed values, from what is said or shown. If the thread does not make the
         appliance clear, null; do not assume an AC because most threads are about ACs.
THREAD:
"""


def _first_name(speaker: str) -> str:
    return speaker.split()[0]


def prompt(thread: list[ThreadMessage]) -> str:
    lines = [
        f"[{m.id}] {_first_name(m.speaker)} ({m.kind}, {m.ts.astimezone(EXPORT_TZ):%Y-%m-%d %H:%M}): {m.text}"
        for m in thread
    ]
    return PROMPT + "\n".join(lines)


def _set(**fields) -> dict:
    # The contract models take a missing optional field as unset, not None.
    return {k: v for k, v in fields.items() if v is not None}


def card_text(card: FaultCard) -> str:
    """The text embedded for a card; search embeds its query against these."""
    parts = (card.brand, card.model, card.error_code, card.symptom, card.root_cause, *card.fix_steps)
    return " ".join(p for p in parts if p)


def card_from_draft(draft: CardDraft, thread: list[ThreadMessage], card_id: str, now: datetime) -> FaultCard | None:
    if not (draft.resolved and draft.symptom and draft.steps):
        return None
    by_id = {m.id: m for m in thread}
    fix = by_id.get(draft.fix_message_id or "")
    # An unclear appliance type is not guessed: a person sets it (T40).
    review = draft.confidence < REVIEW_CONFIDENCE or fix is None or draft.appliance_type is None
    hazard = "none"
    for step in draft.steps:
        level, stop = tag(step.summary_en, step.hazard)
        if stop == "refrigerant":
            level = "refrigerant"
        elif stop:
            # Another hard stop (microwave, CRT, geyser) has no card hazard level: at least HV, and a person decides.
            level = max(level, "HV", key=LEVELS.index)
            review = True
        hazard = max(hazard, level, key=LEVELS.index)
    # Credited as voice only with its stored audio: the source chip must have something to play.
    voice = fix is not None and fix.kind == "voice" and fix.audio_uri is not None
    source = FaultCardSource(
        **_set(
            type="whatsapp_voice" if voice else "whatsapp_text",
            author=fix and _first_name(fix.speaker),
            date=fix and fix.ts.astimezone(EXPORT_TZ).date().isoformat(),
            message_ids=[i for i in draft.message_ids if i in by_id],
            audio_uri=fix.audio_uri if voice else None,
        )
    )
    return FaultCard(
        **_set(
            id=card_id,
            created_at=now,
            # A thread that names no brand gives a general card: search offers it for every brand.
            brand=canonical_brand(draft.brand or ""),
            model=draft.model,
            appliance_type=draft.appliance_type,
            error_code=draft.error_code or "",
            symptom=draft.symptom,
            root_cause=draft.root_cause,
            fix_steps=[s.text for s in draft.steps],
            parts=draft.parts,
            hazard=hazard,
            source=source,
            confidence=draft.confidence,
            language=draft.language,
            review_status="needs_review" if review else "auto",
        )
    )


async def import_cards(threads: list[list[ThreadMessage]], ask: Ask, embed: Embed, store, now: datetime) -> CardCounts:
    """`store` has `nearest(brand, vector, limit)` and `save(card, vector)` (clients.firestore.CardStore)."""
    limit = asyncio.Semaphore(EXTRACT_PARALLEL)

    async def extract(thread: list[ThreadMessage]) -> CardDraft:
        async with limit:
            return await ask(prompt(thread), CardDraft)

    drafts = await asyncio.gather(*(extract(t) for t in threads), return_exceptions=True)
    counts = CardCounts()
    # Written one at a time, so a repeat inside the same import merges into the card written before it.
    for thread, draft in zip(threads, drafts, strict=True):
        if isinstance(draft, Exception):
            # One failed thread is counted in imports.errors[] and does not stop the import. The log gets only the
            # error's class: its text or traceback can carry the prompt, i.e. private chat content.
            logger.error("card extraction failed (%s)", type(draft).__name__)
            counts.errors.append(EXTRACTION_FAILED)
            continue
        card = card_from_draft(draft, thread, f"fc_{uuid4().hex[:16]}", now)
        if card is None:
            continue
        vector = embed([card_text(card)], "RETRIEVAL_DOCUMENT")[0]
        old = match(card, store.nearest(card.brand, vector, MATCH_CANDIDATES))
        if old:
            merged = merge(old, card)
            store.save(merged, embed([card_text(merged)], "RETRIEVAL_DOCUMENT")[0])
            counts.cards_merged += 1
        else:
            store.save(card, vector)
            counts.cards_created += 1
            counts.cards_needing_review += card.review_status == "needs_review"
    return counts
