from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from jobs.ingest.adapter import ENRICHMENT_FAILED, prepare_thread_messages, to_thread_messages
from jobs.ingest.models import Attachment, ExportMessage, MessageEnrichment

INDIA = ZoneInfo("Asia/Kolkata")


def raw_message(
    message_id: str = "m1",
    *,
    timestamp: datetime = datetime(2026, 10, 16, 23, 40),
    text: str = "synthetic text",
    attachment: Attachment | None = None,
) -> ExportMessage:
    return ExportMessage(
        id=message_id,
        speaker="TechA",
        timestamp=timestamp,
        text=text,
        attachment=attachment,
        export_index=int(message_id[1:]) - 1,
    )


def test_adapter_attaches_ist_without_changing_late_night_wall_clock_date():
    adapted = to_thread_messages([raw_message()], import_id="i_night", timezone=INDIA)

    assert adapted[0].id == "i_night:m1"
    assert adapted[0].ts.isoformat() == "2026-10-16T23:40:00+05:30"
    assert adapted[0].ts.date().isoformat() == "2026-10-16"

    with pytest.raises(ValueError, match="timezone"):
        to_thread_messages([raw_message()], import_id="i_night", timezone=None)  # type: ignore[arg-type]


def test_raw_export_message_rejects_an_already_aware_timestamp():
    with pytest.raises(ValidationError, match="local wall-clock"):
        raw_message(timestamp=datetime(2026, 10, 16, 23, 40, tzinfo=INDIA))


def test_adapter_namespaces_the_same_local_message_id_by_import():
    raw = raw_message()

    first = to_thread_messages([raw], import_id="i_ab12", timezone=INDIA)
    second = to_thread_messages([raw], import_id="i_cd34", timezone=INDIA)

    assert first[0].id == "i_ab12:m1"
    assert second[0].id == "i_cd34:m1"
    assert first[0].id != second[0].id


def test_adapter_builds_validated_messages_from_media_enrichment():
    messages = [
        raw_message("m1"),
        raw_message(
            "m2",
            text="",
            attachment=Attachment(filename="note.opus", kind="audio", available=True),
        ),
        raw_message(
            "m3",
            text="",
            attachment=Attachment(filename="photo.jpg", kind="photo", available=True),
        ),
    ]

    adapted = to_thread_messages(
        messages,
        import_id="i_media",
        timezone=INDIA,
        enrichments={
            "m2": MessageEnrichment(text="synthetic transcript", audio_uri="fixture_audio_m2"),
            "m3": MessageEnrichment(text="synthetic photo description"),
        },
    )

    assert [(item.kind, item.text, item.audio_uri) for item in adapted] == [
        ("text", "synthetic text", None),
        ("voice", "synthetic transcript", "fixture_audio_m2"),
        ("photo", "synthetic photo description", None),
    ]


def test_failed_voice_enrichment_keeps_a_safe_voice_message():
    voice = raw_message(
        text="",
        attachment=Attachment(filename="note.opus", kind="audio", available=True),
    )

    adapted = to_thread_messages(
        [voice],
        import_id="i_failed",
        timezone=INDIA,
        enrichments={"m1": MessageEnrichment()},
    )

    assert adapted[0].kind == "voice"
    assert adapted[0].text == ""
    assert adapted[0].audio_uri is None


async def test_enrichment_failures_return_only_fixed_safe_import_errors():
    messages = [
        raw_message(
            "m1",
            text="",
            attachment=Attachment(filename="synthetic-note.opus", kind="audio", available=True),
        ),
        raw_message(
            "m2",
            text="",
            attachment=Attachment(filename="synthetic-photo.jpg", kind="photo", available=True),
        ),
    ]

    async def fail_with_sensitive_details(message: ExportMessage) -> MessageEnrichment:
        raise RuntimeError(
            f"id={message.id} filename={message.attachment.filename} "
            "phone=SYNTHETIC_PHONE chat=SYNTHETIC_PRIVATE_TEXT "
            "url=https://invalid.example/private token=SYNTHETIC_TOKEN"
        )

    result = await prepare_thread_messages(
        messages,
        import_id="i_errors",
        timezone=INDIA,
        enrich=fail_with_sensitive_details,
    )

    assert result.errors == [ENRICHMENT_FAILED, ENRICHMENT_FAILED]
    assert [(message.kind, message.text, message.audio_uri) for message in result.messages] == [
        ("voice", "", None),
        ("photo", "", None),
    ]
    exposed = " ".join(result.errors)
    for sensitive in (
        "m1",
        "synthetic-note.opus",
        "SYNTHETIC_PHONE",
        "SYNTHETIC_PRIVATE_TEXT",
        "invalid.example",
        "SYNTHETIC_TOKEN",
        "RuntimeError",
    ):
        assert sensitive not in exposed


@pytest.mark.parametrize("kind", ["text", "photo"])
def test_adapter_rejects_audio_uri_for_non_voice_messages(kind):
    attachment = None
    if kind == "photo":
        attachment = Attachment(filename="photo.jpg", kind="photo", available=True)

    with pytest.raises(ValueError, match="audio_uri"):
        to_thread_messages(
            [raw_message(text="" if attachment else "synthetic text", attachment=attachment)],
            import_id="i_guard",
            timezone=INDIA,
            enrichments={"m1": MessageEnrichment(text="synthetic enrichment", audio_uri="invalid_audio")},
        )
