"""search_fault_cards (SPEC §6, BUILD-GUIDE T15): the brand's nearest cards to the query text, cards with the exact
error code first, then by similarity. Error codes are exact things, so a code match outranks a closer symptom."""

from collections.abc import Callable

from models.fault_card import FaultCard
from models.tools import CardHit, Citation, SearchFaultCardsIn, SearchFaultCardsOut

Embed = Callable[[list[str], str], list[list[float]]]
Nearest = Callable[[str, list[float], int], list[tuple[FaultCard, float]]]

MAX_RESULTS = 5
# Fetched from the vector query before ranking, so a code match outside the nearest 5 still surfaces.
CANDIDATES = 20


def _code(code: str | None) -> str:
    return (code or "").strip().upper()


def _hit(card: FaultCard) -> CardHit:
    src = card.source
    return CardHit(
        card_id=card.id,
        brand=card.brand,
        model=card.model,
        error_code=card.error_code,
        symptom=card.symptom,
        root_cause=card.root_cause,
        hazard=card.hazard,
        steps=len(card.fix_steps),
        confidence=card.confidence,
        verified_count=card.verified_count,
        citation=Citation(author=src.author, date=src.date and src.date.isoformat(), audio_uri=src.audio_uri),
    )


def search_fault_cards(inp: SearchFaultCardsIn, embed: Embed, nearest: Nearest) -> SearchFaultCardsOut:
    text = " ".join(x for x in (inp.brand, inp.model, inp.error_code, inp.symptom) if x)
    candidates = nearest(inp.brand, embed([text], "RETRIEVAL_QUERY")[0], CANDIDATES)
    code = _code(inp.error_code)
    ranked = sorted(candidates, key=lambda c: (bool(code) and _code(c[0].error_code) == code, c[1]), reverse=True)
    return SearchFaultCardsOut(cards=[_hit(card) for card, _ in ranked[:MAX_RESULTS]])
