"""Card dedupe (SPEC §4): a new card merges into an existing one of the same brand and code when their embeddings
are closer than MERGE_SIMILARITY. A fix that disagrees reads differently, so it stays a separate card."""

from models.fault_card import FaultCard

MERGE_SIMILARITY = 0.9
LEVELS = ["none", "HV", "capacitor", "refrigerant"]
# The English fields move with the words they translate.
CONTENT = {"model", "series", "year_range", "appliance_type", "symptom", "root_cause", "fix_steps", "parts", "language"}
CONTENT |= {"symptom_en", "root_cause_en", "fix_steps_en"}


def match(card: FaultCard, candidates: list[tuple[FaultCard, float]]) -> FaultCard | None:
    """`candidates` are the brand's nearest cards with their cosine similarity to `card`."""
    return next(
        (c for c, sim in candidates if c.error_code == card.error_code and sim > MERGE_SIMILARITY),
        None,
    )


def merge(old: FaultCard, new: FaultCard) -> FaultCard:
    """Keeps the first card's id and credited speaker (unless only the new one has a voice note), adds the new thread's messages, takes the surer card's
    content, and never lowers the hazard or undoes a human review."""
    surer = new if new.confidence > old.confidence else old
    # A voice note is what the source chip plays, so it takes the credit from a first card that has none.
    credit = new.source if new.source.audio_uri and not old.source.audio_uri else old.source
    old_message_ids = old.source.message_ids or []
    new_message_ids = new.source.message_ids or []
    has_new_evidence = bool(set(new_message_ids) - set(old_message_ids))
    source = credit.model_copy(
        update={"message_ids": list(dict.fromkeys([*old_message_ids, *new_message_ids]))}
    )
    human = old.review_status in ("approved", "rejected")
    return old.model_copy(
        update={k: getattr(surer, k) for k in CONTENT}
        | {
            "source": source,
            "confidence": surer.confidence,
            "verified_count": old.verified_count + has_new_evidence,
            "hazard": max(old.hazard, new.hazard, key=LEVELS.index),
            "review_status": old.review_status if human else surer.review_status,
        }
    )
