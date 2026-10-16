from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from jobs.ingest.adapter import to_thread_messages
from jobs.ingest.models import Attachment, ExportMessage, MessageEnrichment
from jobs.ingest.threads import fallback_threads, group_thread_messages, topic_threads
from models.imports import ThreadMessage

INDIA = ZoneInfo("Asia/Kolkata")


def message(message_id: str, hour: int, minute: int) -> ThreadMessage:
    return ThreadMessage(
        id=message_id,
        speaker="TechA",
        ts=datetime(2026, 10, 16, hour, minute, tzinfo=INDIA),
        kind="text",
        text=f"synthetic-{message_id}",
    )


class FakeThreadClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.received: list[ThreadMessage] = []

    async def group_threads(self, messages: list[ThreadMessage]):
        self.received = messages
        if self.error is not None:
            raise self.error
        return self.response


async def test_valid_topic_grouping_receives_eligible_messages_in_time_order():
    client = FakeThreadClient({"groups": [["i_test:m1", "i_test:m2"], ["i_test:m3"]]})

    result = await topic_threads(
        [message("i_test:m2", 9, 10), message("i_test:m1", 9, 0), message("i_test:m3", 9, 20)],
        client,
    )

    assert [item.id for item in client.received] == ["i_test:m1", "i_test:m2", "i_test:m3"]
    assert result.groups == [["i_test:m1", "i_test:m2"], ["i_test:m3"]]


@pytest.mark.parametrize(
    "response",
    [
        {"groups": [["i_test:m1", "i_test:m1"], ["i_test:m2", "i_test:m3"]]},
        {"groups": [["i_test:m1", "i_test:m2"]]},
        {"groups": [["i_test:m1", "i_test:m2", "i_test:m_unknown"]]},
        {"groups": [["i_test:m2", "i_test:m1", "i_test:m3"]]},
        {"threads": [["i_test:m1", "i_test:m2", "i_test:m3"]]},
    ],
    ids=["duplicate", "missing", "unknown", "out-of-order", "malformed"],
)
async def test_invalid_topic_grouping_uses_time_gap_fallback(response):
    messages = [message("i_test:m1", 9, 0), message("i_test:m2", 9, 10), message("i_test:m3", 9, 20)]

    result = await topic_threads(messages, FakeThreadClient(response))

    assert result.groups == [["i_test:m1", "i_test:m2", "i_test:m3"]]


async def test_flash_failure_falls_back_and_exactly_thirty_minutes_stays_together():
    messages = [message("i_test:m1", 9, 0), message("i_test:m2", 9, 30), message("i_test:m3", 10, 1)]

    result = await topic_threads(messages, FakeThreadClient(error=ConnectionError("offline synthetic failure")))

    assert result == fallback_threads(messages)
    assert result.groups == [["i_test:m1", "i_test:m2"], ["i_test:m3"]]


async def test_valid_topic_grouping_can_join_a_late_answer_to_its_question():
    messages = [message("i_test:m1", 9, 0), message("i_test:m2", 13, 0)]

    result = await topic_threads(messages, FakeThreadClient({"groups": [["i_test:m1", "i_test:m2"]]}))

    assert result.groups == [["i_test:m1", "i_test:m2"]]


async def test_valid_topic_grouping_can_start_a_new_fault_two_minutes_after_an_outcome():
    messages = [message("i_test:m1", 9, 0), message("i_test:m2", 9, 2)]

    result = await topic_threads(messages, FakeThreadClient({"groups": [["i_test:m1"], ["i_test:m2"]]}))

    assert result.groups == [["i_test:m1"], ["i_test:m2"]]


async def test_topic_grouping_receives_enriched_voice_and_photo_text():
    raw = [
        ExportMessage(
            id="m1",
            speaker="TechA",
            timestamp=datetime(2026, 10, 16, 9, 0),
            text="",
            attachment=Attachment(filename="note.opus", kind="audio", available=True),
            export_index=0,
        ),
        ExportMessage(
            id="m2",
            speaker="TechB",
            timestamp=datetime(2026, 10, 16, 9, 1),
            text="",
            attachment=Attachment(filename="photo.jpg", kind="photo", available=True),
            export_index=1,
        ),
    ]
    enriched = to_thread_messages(
        raw,
        import_id="i_enriched",
        timezone=INDIA,
        enrichments={
            "m1": MessageEnrichment(text="synthetic transcript", audio_uri="fixture_audio_m1"),
            "m2": MessageEnrichment(text="synthetic photo description"),
        },
    )
    client = FakeThreadClient({"groups": [["i_enriched:m1", "i_enriched:m2"]]})

    grouped = await group_thread_messages(enriched, client)

    assert [(item.kind, item.text) for item in client.received] == [
        ("voice", "synthetic transcript"),
        ("photo", "synthetic photo description"),
    ]
    assert grouped == [enriched]
