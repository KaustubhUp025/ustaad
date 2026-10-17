"""Card extraction (BUILD-GUIDE T15, §7.4): a Flash draft becomes a FaultCard or nothing, credited to the message that
states the fix, hazard raised by the tagger, low confidence sent to review; then the import writes, merges and counts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from jobs.ingest.cards import EXTRACTION_FAILED, card_from_draft, card_text, import_cards
from models.imports import CardDraft, ThreadMessage
from tests.unit.fake_cards import FakeCardStore, embed

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)

# Placeholder text only: no error-code meanings or repair guidance.
THREAD = [
    ThreadMessage(id="m1", speaker="Kaustubh Upadhyay", ts="2026-10-16T23:40:00+05:30", kind="text",
                  text="Test question about a Voltas unit showing E6"),
    ThreadMessage(id="m2", speaker="Samyak Jain", ts="2026-10-17T00:30:00+05:30", kind="voice",
                  text="Test answer transcript", audio_uri="gs://b/imports/i_1/PTT-1.flac"),
    ThreadMessage(id="m3", speaker="Kaustubh Upadhyay", ts="2026-10-17T00:45:00+05:30", kind="text",
                  text="Test outcome: it worked"),
]


def draft(**changes) -> CardDraft:
    fields = {
        "resolved": True,
        "brand": "Voltas",
        "model": None,
        "appliance_type": "split_ac",
        "error_code": "E6",
        "symptom": "Test symptom",
        "root_cause": "Test cause",
        "steps": [{"text": "Test step one", "summary_en": "Test step one", "hazard": "none"}],
        "parts": [],
        "fix_message_id": "m2",
        "message_ids": ["m1", "m2", "m3"],
        "confidence": 0.9,
        "language": "hi-Latn",
    }
    return CardDraft(**(fields | changes))


def test_an_unresolved_thread_gives_no_card():
    assert card_from_draft(draft(resolved=False), THREAD, "fc_1", NOW) is None


def test_the_card_credits_the_fix_message_speaker_by_first_name_with_the_ist_date_and_audio():
    card = card_from_draft(draft(), THREAD, "fc_1", NOW)
    assert card.source.model_dump(exclude_none=True) == {
        "type": "whatsapp_voice",
        "author": "Samyak",
        "date": datetime(2026, 10, 17).date(),
        "message_ids": ["m1", "m2", "m3"],
        "audio_uri": "gs://b/imports/i_1/PTT-1.flac",
    }
    assert (card.id, card.brand, card.error_code, card.review_status) == ("fc_1", "Voltas", "E6", "auto")
    assert card.verified_count == 1


def test_a_text_fix_has_no_audio():
    card = card_from_draft(draft(fix_message_id="m3"), THREAD, "fc_1", NOW)
    assert (card.source.type, card.source.audio_uri, card.source.author) == ("whatsapp_text", None, "Kaustubh")


def test_a_voice_note_whose_audio_was_not_stored_is_not_credited_as_voice():
    thread = [*THREAD[:1], THREAD[1].model_copy(update={"audio_uri": None}), *THREAD[2:]]
    card = card_from_draft(draft(), thread, "fc_1", NOW)
    assert (card.source.type, card.source.audio_uri, card.source.author) == ("whatsapp_text", None, "Samyak")


def test_message_ids_not_in_the_thread_are_dropped():
    card = card_from_draft(draft(message_ids=["m2", "m9"]), THREAD, "fc_1", NOW)
    assert card.source.message_ids == ["m2"]


def test_ids_returned_without_the_import_prefix_still_credit_the_message():
    # Real run (Oct 17): Flash sometimes answered "m59" for "i_wa_1017a:m59"; the card lost its author and audio.
    thread = [m.model_copy(update={"id": f"i_1:{m.id}"}) for m in THREAD]
    card = card_from_draft(draft(fix_message_id="m2", message_ids=["m1", "i_1:m2", "m3"]), thread, "fc_1", NOW)
    assert (card.source.author, card.source.audio_uri) == ("Samyak", "gs://b/imports/i_1/PTT-1.flac")
    assert card.source.message_ids == ["i_1:m1", "i_1:m2", "i_1:m3"]
    assert card.review_status == "auto"


def test_an_unknown_fix_message_goes_to_review_without_an_author():
    card = card_from_draft(draft(fix_message_id="m9"), THREAD, "fc_1", NOW)
    assert card.review_status == "needs_review"
    assert card.source.author is None


def test_confidence_below_the_floor_goes_to_review():
    assert card_from_draft(draft(confidence=0.59), THREAD, "fc_1", NOW).review_status == "needs_review"
    assert card_from_draft(draft(confidence=0.6), THREAD, "fc_1", NOW).review_status == "auto"


def test_the_tagger_raises_a_step_hazard_the_draft_set_too_low():
    steps = [
        {"text": "Test step one", "summary_en": "Test step at the filter", "hazard": "none"},
        {"text": "Test step two", "summary_en": "Test step at the outdoor terminals", "hazard": "none"},
    ]
    assert card_from_draft(draft(steps=steps), THREAD, "fc_1", NOW).hazard == "HV"


def test_the_tagger_never_lowers_the_draft_hazard():
    steps = [{"text": "Test step", "summary_en": "Test step at the filter", "hazard": "capacitor"}]
    assert card_from_draft(draft(steps=steps), THREAD, "fc_1", NOW).hazard == "capacitor"


def test_a_gas_step_makes_the_card_refrigerant():
    steps = [{"text": "Test step", "summary_en": "Test step with gas", "hazard": "none"}]
    assert card_from_draft(draft(steps=steps), THREAD, "fc_1", NOW).hazard == "refrigerant"


def test_another_hard_stop_sends_the_card_to_review():
    steps = [{"text": "Test step", "summary_en": "Test step near the magnetron", "hazard": "none"}]
    card = card_from_draft(draft(steps=steps), THREAD, "fc_1", NOW)
    assert (card.hazard, card.review_status) == ("HV", "needs_review")


def test_no_code_is_stored_as_an_empty_code():
    assert card_from_draft(draft(error_code=None), THREAD, "fc_1", NOW).error_code == ""


def test_a_thread_that_names_no_brand_gives_a_general_card():
    card = card_from_draft(draft(brand=None), THREAD, "fc_1", NOW)
    assert (card.brand, card.review_status) == ("", "auto")


def test_a_resolved_draft_without_symptom_or_steps_gives_no_card():
    assert card_from_draft(draft(symptom=None), THREAD, "fc_1", NOW) is None
    assert card_from_draft(draft(steps=[]), THREAD, "fc_1", NOW) is None


def test_a_non_ac_thread_keeps_its_type():
    card = card_from_draft(draft(appliance_type="washing_machine"), THREAD, "fc_1", NOW)
    assert (card.appliance_type, card.review_status) == ("washing_machine", "auto")


def test_an_unclear_appliance_type_goes_to_review():
    card = card_from_draft(draft(appliance_type=None), THREAD, "fc_1", NOW)
    assert card.appliance_type is None
    assert card.review_status == "needs_review"


def test_the_brand_is_stored_in_one_spelling():
    assert card_from_draft(draft(brand="VOLTAS"), THREAD, "fc_1", NOW).brand == "Voltas"


async def test_import_writes_new_cards_merges_a_repeat_and_counts_review():
    second = [m.model_copy(update={"id": f"n{m.id[1:]}"}) for m in THREAD]
    drafts = {
        "m1": draft(),
        "n1": draft(fix_message_id="n2", message_ids=["n1", "n2", "n3"]),
        "x1": draft(resolved=False),
        "y1": draft(error_code="E5", symptom="Other test symptom", confidence=0.4, fix_message_id="y1",
                    message_ids=["y1"]),
    }
    unanswered = [THREAD[0].model_copy(update={"id": "x1"})]
    low = [THREAD[1].model_copy(update={"id": "y1"})]

    async def ask(prompt: str, schema: type) -> CardDraft:
        return next(d for first_id, d in drafts.items() if f"[{first_id}]" in prompt)

    store = FakeCardStore()
    counts = await import_cards([THREAD, second, unanswered, low], ask, embed, store, NOW)
    assert (counts.cards_created, counts.cards_merged, counts.cards_needing_review) == (2, 1, 1)
    e6 = next(card for card, _ in store.cards.values() if card.error_code == "E6")
    assert e6.verified_count == 2
    assert e6.source.message_ids == ["m1", "m2", "m3", "n1", "n2", "n3"]


async def test_the_prompt_carries_the_thread_and_the_use_only_what_is_said_rule():
    seen = []

    async def ask(prompt: str, schema: type) -> CardDraft:
        seen.append(prompt)
        return draft(resolved=False)

    await import_cards([THREAD], ask, embed, FakeCardStore(), NOW)
    assert "[m2] Samyak (voice" in seen[0]
    assert "Test answer transcript" in seen[0]
    assert "Never add an error-code meaning" in seen[0]
    assert "appliance_type" in seen[0]
    assert "never guess the brand" in seen[0]


async def test_a_failed_extraction_is_listed_and_the_other_threads_still_import():
    async def ask(prompt: str, schema: type) -> CardDraft:
        if "[x1]" in prompt:
            raise RuntimeError("Test failure")
        return draft()

    store = FakeCardStore()
    counts = await import_cards([[THREAD[0].model_copy(update={"id": "x1"})], THREAD], ask, embed, store, NOW)
    assert counts.cards_created == 1
    assert counts.errors == [EXTRACTION_FAILED]


async def test_an_extraction_error_never_carries_the_exception_text():
    secret = "gs://b/imports/i_1/PTT-1.flac token=abc123 +919876543210 Traceback (most recent call last)"

    async def ask(prompt: str, schema: type) -> CardDraft:
        raise RuntimeError(secret)

    counts = await import_cards([THREAD], ask, embed, FakeCardStore(), NOW)
    assert counts.errors == [EXTRACTION_FAILED]
    assert not any(part in counts.model_dump_json() for part in ("gs://", "token", "+91", "Traceback", "m1"))


async def test_a_failed_extraction_logs_only_a_fixed_message(caplog):
    secret = "gs://b/imports/i_1/PTT-1.flac token=abc123 +919876543210 Samyak bhai E6 aa raha"

    async def ask(prompt: str, schema: type) -> CardDraft:
        raise RuntimeError(secret)

    with caplog.at_level("DEBUG"):
        await import_cards([THREAD], ask, embed, FakeCardStore(), NOW)
    logged = "\n".join(r.getMessage() + (r.exc_text or "") + str(r.exc_info or "") for r in caplog.records)
    assert "card extraction failed" in logged
    assert not any(part in logged for part in ("gs://", "token", "+91", "Samyak", "E6", "RuntimeError(", "m1"))


def test_only_a_voice_message_carries_audio():
    for kind in ("text", "photo"):
        with pytest.raises(ValidationError):
            ThreadMessage(id="m9", speaker="Samyak Jain", ts="2026-10-16T10:00:00+05:30", kind=kind, text="Test",
                          audio_uri="gs://b/a.flac")
    voice = ThreadMessage(id="m9", speaker="Samyak Jain", ts="2026-10-16T10:00:00+05:30", kind="voice", text="Test")
    assert voice.audio_uri is None


def test_the_card_keeps_the_drafts_english_beside_the_words_as_said():
    steps = [
        {"text": "Test pehla step", "summary_en": "Test first step", "hazard": "none"},
        {"text": "Test doosra step", "summary_en": "Test second step", "hazard": "none"},
    ]
    english = draft(steps=steps, symptom_en="Test symptom en", root_cause_en="Test cause en")
    card = card_from_draft(english, THREAD, "fc_1", NOW)
    assert card.fix_steps == ["Test pehla step", "Test doosra step"]
    assert card.fix_steps_en == ["Test first step", "Test second step"]
    assert (card.symptom, card.symptom_en, card.root_cause_en) == ("Test symptom", "Test symptom en", "Test cause en")


def test_a_draft_without_english_symptom_leaves_it_unset():
    public = card_from_draft(draft(), THREAD, "fc_1", NOW).to_public_dict()
    assert "symptom_en" not in public and "root_cause_en" not in public


ENGLISH = {"symptom_en": "Test English symptom", "root_cause_en": "Test English cause", "fix_steps_en": ["Test en"]}


def test_the_stored_english_never_changes_the_embedded_text():
    card = card_from_draft(draft(), THREAD, "fc_1", NOW)
    for changed in ({k: None for k in ENGLISH}, ENGLISH, {"fix_steps_en": ["Test capacitor gas brazing"]}):
        assert card_text(card.model_copy(update=changed)) == card_text(card)


@pytest.mark.parametrize(
    ("changes", "stripped"),
    [
        ({"steps": [{"text": "Test step one", "summary_en": " ", "hazard": "none"}]}, {"fix_steps_en"}),
        ({"symptom_en": "", "root_cause_en": "Test English cause"}, {"symptom_en"}),
        ({"symptom_en": "Test English symptom", "root_cause_en": "  "}, {"root_cause_en"}),
    ],
)
async def test_an_unusable_english_line_strips_only_that_english_and_the_card_is_still_saved(changes, stripped):
    async def ask(prompt: str, schema: type) -> CardDraft:
        return draft(**{"symptom_en": "Test English symptom", "root_cause_en": "Test English cause"} | changes)

    store = FakeCardStore()
    counts = await import_cards([THREAD], ask, embed, store, NOW)
    ((card, _),) = store.cards.values()
    assert counts.cards_created == 1
    assert (card.symptom, card.root_cause, card.fix_steps) == ("Test symptom", "Test cause", ["Test step one"])
    public = card.to_public_dict()
    assert stripped.isdisjoint(public) and (set(ENGLISH) - stripped) <= set(public)
    assert (card.hazard, card.review_status) == (card_from_draft(draft(), THREAD, "fc_2", NOW).hazard, "auto")
