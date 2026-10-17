"""Dedupe (SPEC §4): same brand and code with cosine above the threshold merges, crediting both threads."""

from jobs.ingest.dedupe import match, merge
from models.fault_card import FaultCard


def card(cid="fc_old", code="E6", confidence=0.8, hazard="none", review="auto", ids=("m1",), symptom="Test symptom"):
    return FaultCard(
        id=cid,
        created_at="2026-10-16T00:00:00Z",
        brand="Voltas",
        error_code=code,
        symptom=symptom,
        fix_steps=[f"Test step from {cid}"],
        hazard=hazard,
        source={"type": "whatsapp_voice", "author": cid, "date": "2026-10-16", "message_ids": list(ids)},
        confidence=confidence,
        review_status=review,
    )


def test_same_code_above_the_threshold_matches():
    old = card()
    assert match(card(cid="fc_new"), [(old, 0.95)]) is old


def test_a_different_code_never_matches_however_close():
    assert match(card(cid="fc_new", code="E5"), [(card(), 0.99)]) is None


def test_the_threshold_itself_does_not_match():
    assert match(card(cid="fc_new"), [(card(), 0.9)]) is None


def test_two_cards_without_a_code_can_match():
    old = card(code="")
    assert match(card(cid="fc_new", code=""), [(old, 0.95)]) is old


def test_merge_keeps_the_first_card_and_credit_and_adds_the_new_messages():
    merged = merge(card(ids=("m1", "m2")), card(cid="fc_new", ids=("n1",), confidence=0.7))
    assert (merged.id, merged.source.author, merged.verified_count) == ("fc_old", "fc_old", 2)
    assert merged.source.message_ids == ["m1", "m2", "n1"]
    assert merged.fix_steps == ["Test step from fc_old"]


def test_merge_takes_the_surer_cards_content():
    merged = merge(card(confidence=0.5, review="needs_review"), card(cid="fc_new", confidence=0.9))
    assert (merged.id, merged.fix_steps, merged.confidence) == ("fc_old", ["Test step from fc_new"], 0.9)
    assert merged.review_status == "auto"


def test_merge_never_lowers_the_hazard():
    assert merge(card(hazard="capacitor"), card(cid="fc_new", hazard="HV", confidence=0.9)).hazard == "capacitor"


def test_merge_keeps_a_human_review_decision():
    assert merge(card(review="approved"), card(cid="fc_new", confidence=0.4, review="needs_review")).review_status == (
        "approved"
    )


def test_merge_lists_a_message_once():
    assert merge(card(ids=("m1", "m2")), card(cid="fc_new", ids=("m2", "n1"))).source.message_ids == ["m1", "m2", "n1"]


def test_duplicate_retry_does_not_inflate_verified_count():
    old = card(ids=("m1", "m2"))
    old = old.model_copy(update={"verified_count": 3})

    assert merge(old, card(cid="fc_retry", ids=("m1", "m2"))).verified_count == 3


def test_genuinely_new_message_evidence_increments_verified_count():
    old = card(ids=("m1", "m2"))
    old = old.model_copy(update={"verified_count": 3})

    assert merge(old, card(cid="fc_new", ids=("m2", "m3"))).verified_count == 4


def test_a_voice_source_replaces_a_first_card_without_audio():
    text = card()
    text = text.model_copy(update={"source": text.source.model_copy(update={"type": "whatsapp_text"})})
    voice = card(cid="fc_new", ids=("n1",))
    voice = voice.model_copy(update={"source": voice.source.model_copy(update={"audio_uri": "gs://b/n.flac"})})
    source = merge(text, voice).source
    assert (source.type, source.author, source.audio_uri) == ("whatsapp_voice", "fc_new", "gs://b/n.flac")
    assert source.message_ids == ["m1", "n1"]


def test_a_first_card_with_audio_keeps_its_credit():
    first = card()
    first = first.model_copy(update={"source": first.source.model_copy(update={"audio_uri": "gs://b/m.flac"})})
    second = card(cid="fc_new", ids=("n1",))
    second = second.model_copy(update={"source": second.source.model_copy(update={"audio_uri": "gs://b/n.flac"})})
    assert merge(first, second).source.audio_uri == "gs://b/m.flac"
