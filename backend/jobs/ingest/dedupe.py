"""Card dedupe (SPEC §4): a new card merges into an existing one of the same brand and code when their embeddings
are closer than MERGE_SIMILARITY. A fix that disagrees reads differently, so it stays a separate card."""

from models.fault_card import FaultCard

MERGE_SIMILARITY = 0.9
LEVELS = ["none", "HV", "capacitor", "refrigerant"]
CONTENT = {"model", "series", "year_range", "appliance_type", "symptom", "root_cause", "fix_steps", "parts", "language"}


def match(card: FaultCard, candidates: list[tuple[FaultCard, float]]) -> FaultCard | None:
    """`candidates` are the brand's nearest cards with their cosine similarity to `card`."""
    return next(
        (c for c, sim in candidates if c.error_code == card.error_code and sim > MERGE_SIMILARITY),
        None,
    )


def merge(old: FaultCard, new: FaultCard) -> FaultCard:
    """Keeps the first card's id and credited speaker, adds the new thread's messages, takes the surer card's
    content, and never lowers the hazard or undoes a human review."""
    surer = new if new.confidence > old.confidence else old
    source = old.source.model_copy(
        update={"message_ids": list(dict.fromkeys([*(old.source.message_ids or []), *(new.source.message_ids or [])]))}
    )
    human = old.review_status in ("approved", "rejected")
    return old.model_copy(
        update={k: getattr(surer, k) for k in CONTENT}
        | {
            "source": source,
            "confidence": surer.confidence,
            "verified_count": old.verified_count + 1,
            "hazard": max(old.hazard, new.hazard, key=LEVELS.index),
            "review_status": old.review_status if human else surer.review_status,
        }
    )
