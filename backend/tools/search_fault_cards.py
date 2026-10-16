"""search_fault_cards (SPEC §6, BUILD-GUIDE T15, T41): the brand's nearest cards to the query text, optionally only
one appliance type, cards with the exact error code first, then by similarity. Error codes are exact things, so a
code match of the asked brand outranks a closer symptom and is kept even below the relevance floor; a code means
nothing across brands, so a general card's code earns nothing."""

from collections.abc import Callable

from models.fault_card import FaultCard
from models.tools import CardHit, Citation, SearchFaultCardsIn, SearchFaultCardsOut

Embed = Callable[[list[str], str], list[list[float]]]
Nearest = Callable[[str, list[float], int], list[tuple[FaultCard, float]]]

MAX_RESULTS = 5
# Fetched from the vector query before filtering and ranking, so a code match or a card of the asked type outside
# the nearest 5 still surfaces. Filtering in code needs no extra Firestore index (T41).
CANDIDATES = 20
# Cosine similarity below which a card is not about the question. Measured Oct 16 with gemini-embedding-001 at 768
# dims on 3 cards and 10 queries: right answers 0.76-0.81, other appliances 0.50-0.61, but a wrong fault of the
# same brand still 0.73. Recheck on the full export.
RELEVANCE_FLOOR = 0.65
# Brands this short are written in capitals (LG, IFB, BPL); longer ones capitalised (Voltas, Blue Star).
ACRONYM_MAX = 3


def canonical_brand(brand: str) -> str:
    """One spelling per brand, so Firestore's exact brand filter ignores case and spacing."""
    words = brand.split()
    return " ".join(w.upper() if len(w) <= ACRONYM_MAX else w.capitalize() for w in words)


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
    brand = canonical_brand(inp.brand)
    text = " ".join(x for x in (brand, inp.model, inp.error_code, inp.symptom) if x)
    code = _code(inp.error_code)
    vector = embed([text], "RETRIEVAL_QUERY")[0]
    # General cards (no brand named in the thread) apply to every brand.
    candidates = nearest(brand, vector, CANDIDATES) + (nearest("", vector, CANDIDATES) if brand else [])
    ranked = sorted(
        (
            (bool(code) and card.brand == brand and _code(card.error_code) == code, sim, card)
            for card, sim in candidates
            if inp.appliance_type is None or card.appliance_type == inp.appliance_type
        ),
        key=lambda hit: hit[:2],
        reverse=True,
    )
    kept = [card for exact, sim, card in ranked if exact or sim >= RELEVANCE_FLOOR]
    return SearchFaultCardsOut(cards=[_hit(card) for card in kept[:MAX_RESULTS]])
