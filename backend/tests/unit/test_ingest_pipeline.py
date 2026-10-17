from datetime import UTC, datetime

from jobs.ingest.cards import EXTRACTION_FAILED
from jobs.ingest.models import MessageEnrichment
from jobs.ingest.pipeline import AMBIGUOUS_DATE, ImportLifecycle, run_import_pipeline
from models.imports import CardDraft, DraftStep


class FakeThreadClient:
    async def group_threads(self, messages):
        return {"groups": [[message.id] for message in messages]}


class FakeStore:
    def __init__(self):
        self.saved = []

    def nearest(self, brand, vector, limit):
        return []

    def save(self, card, vector):
        self.saved.append(card)


def _draft(message_id: str) -> CardDraft:
    return CardDraft(
        resolved=True,
        brand="Voltas",
        model=None,
        appliance_type="split_ac",
        error_code="E6",
        symptom="Synthetic symptom",
        root_cause=None,
        steps=[DraftStep(text="Synthetic fix", summary_en="Inspect the connector", hazard="none")],
        parts=[],
        fix_message_id=message_id,
        message_ids=[message_id],
        confidence=0.9,
        language="en",
    )


async def _enrich(message):
    return MessageEnrichment(text=message.text)


def _embed(texts, task_type):
    return [[0.1, 0.2] for _ in texts]


async def test_successful_pipeline_reports_lifecycle_and_card_counts():
    lifecycle = []
    store = FakeStore()

    async def extract(prompt, schema):
        message_id = prompt.split("[", 1)[1].split("]", 1)[0]
        return _draft(message_id)

    result = await run_import_pipeline(
        b"16/10/26, 9:00 am - Asha: Synthetic resolved fault",
        import_id="i_pipeline",
        archive_filenames=(),
        enrich=_enrich,
        thread_client=FakeThreadClient(),
        ask=extract,
        embed=_embed,
        store=store,
        now=datetime(2026, 10, 16, 10, 0, tzinfo=UTC),
        on_lifecycle=lifecycle.append,
    )

    assert lifecycle == [
        ImportLifecycle.PARSING,
        ImportLifecycle.TRANSCRIBING,
        ImportLifecycle.EXTRACTING,
        ImportLifecycle.DONE,
    ]
    assert result.status is ImportLifecycle.DONE
    assert result.card_counts.cards_created == 1
    assert result.card_counts.cards_needing_review == 0
    assert result.card_counts.cards_merged == 0
    assert result.errors == []
    assert len(store.saved) == 1


async def test_entirely_ambiguous_date_fails_with_fixed_safe_result():
    lifecycle = []

    result = await run_import_pipeline(
        b"01/02/26, 9:00 am - Asha: Synthetic message",
        import_id="i_ambiguous",
        archive_filenames=(),
        enrich=_enrich,
        thread_client=FakeThreadClient(),
        ask=lambda prompt, schema: None,
        embed=_embed,
        store=FakeStore(),
        now=datetime(2026, 10, 16, 10, 0, tzinfo=UTC),
        on_lifecycle=lifecycle.append,
    )

    assert lifecycle == [ImportLifecycle.PARSING, ImportLifecycle.FAILED]
    assert result.status is ImportLifecycle.FAILED
    assert result.errors == [AMBIGUOUS_DATE]
    assert result.card_counts.cards_created == 0


async def test_unexpected_failure_exposes_only_a_fixed_safe_error(caplog):
    lifecycle = []
    private = "private-name.opus token=SYNTHETIC_TOKEN gs://private/content"

    async def leaking_enricher(message):
        raise RuntimeError(private)

    class FailingThreadClient:
        async def group_threads(self, messages):
            raise RuntimeError(private)

    result = await run_import_pipeline(
        b"16/10/26, 9:00 am - Asha: note.opus (file attached)",
        import_id="i_safe",
        archive_filenames=("note.opus",),
        enrich=leaking_enricher,
        thread_client=FailingThreadClient(),
        ask=lambda prompt, schema: None,
        embed=_embed,
        store=FakeStore(),
        now=datetime(2026, 10, 16, 10, 0, tzinfo=UTC),
        on_lifecycle=lifecycle.append,
    )

    exposed = " ".join(result.errors) + caplog.text
    assert result.status is ImportLifecycle.DONE
    assert private not in exposed
    assert "SYNTHETIC_TOKEN" not in exposed
    assert "gs://" not in exposed


async def test_card_failure_does_not_prevent_later_thread_processing():
    calls = 0
    store = FakeStore()

    async def extract(prompt, schema):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private first thread content")
        message_id = prompt.split("[", 1)[1].split("]", 1)[0]
        return _draft(message_id)

    result = await run_import_pipeline(
        (
            b"16/10/26, 9:00 am - Asha: First synthetic fault\n"
            b"16/10/26, 9:01 am - Dev: Second synthetic fault"
        ),
        import_id="i_continue",
        archive_filenames=(),
        enrich=_enrich,
        thread_client=FakeThreadClient(),
        ask=extract,
        embed=_embed,
        store=store,
        now=datetime(2026, 10, 16, 10, 0, tzinfo=UTC),
        on_lifecycle=lambda status: None,
    )

    assert calls == 2
    assert len(store.saved) == 1
    assert result.card_counts.cards_created == 1
    assert result.errors == [EXTRACTION_FAILED]
