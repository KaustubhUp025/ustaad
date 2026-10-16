from datetime import datetime
from pathlib import Path

import pytest

from jobs.ingest.parse import AmbiguousDateOrderError, DateOrder, parse_chat

FIXTURES = Path(__file__).parents[3] / "seed/whatsapp_export_small"


def test_android_fixture_parses_authored_messages_and_attachments():
    parsed = parse_chat(
        (FIXTURES / "android_chat.txt").read_bytes(),
        archive_filenames={"PTT-20261013-WA0001.opus"},
    )

    assert parsed.platform == "android"
    assert parsed.date_order == "day_first"
    assert [message.id for message in parsed.messages] == [f"m{i}" for i in range(1, 7)]
    assert parsed.messages[0].timestamp == datetime(2026, 10, 13, 9, 1)
    assert all(message.timestamp.tzinfo is None for message in parsed.messages)
    assert parsed.messages[0].text == "Namaste Dev safe"
    assert all(
        control not in message.text
        for message in parsed.messages
        for control in "\u200e\u200f\u2066\u2067\u2068\u2069"
    )
    assert {message.speaker for message in parsed.messages} == {"Asha", "Dev", "Participant 1"}
    assert all("deleted" not in message.text.lower() for message in parsed.messages)
    assert all("encrypted" not in message.text.lower() for message in parsed.messages)
    assert parsed.messages[1].text == ""
    assert parsed.messages[2].attachment.model_dump() == {
        "filename": "PTT-20261013-WA0001.opus",
        "kind": "audio",
        "available": True,
    }
    assert parsed.messages[3].attachment.model_dump() == {
        "filename": "IMG-20261013-WA0002.jpg",
        "kind": "photo",
        "available": False,
    }
    assert parsed.messages[4].text == "First line\nsecond line"
    assert parsed.messages[5].speaker == "Participant 1"

def test_parser_sorts_by_local_time_then_archive_order_before_assigning_ids():
    chat = (
        b"13/10/26, 9:02 am - Dev Kumar: Later\n"
        b"13/10/26, 9:01 am - Asha Sharma: Earlier\n"
        b"13/10/26, 9:02 am - Asha Sharma: Same time\n"
    )

    parsed = parse_chat(chat)

    assert [(message.id, message.text, message.export_index) for message in parsed.messages] == [
        ("m1", "Earlier", 1),
        ("m2", "Later", 0),
        ("m3", "Same time", 2),
    ]


def test_ios_utf8_bom_and_month_first_syntax():
    data = b"\xef\xbb\xbf" + (FIXTURES / "ios_chat.txt").read_bytes()

    parsed = parse_chat(data, archive_filenames={"IMG-20261013-WA0003.jpg"})

    assert parsed.platform == "ios"
    assert parsed.date_order == "month_first"
    assert len(parsed.messages) == 2
    assert parsed.messages[0].timestamp == datetime(2026, 10, 13, 9, 0)
    assert parsed.messages[1].attachment.model_dump() == {
        "filename": "IMG-20261013-WA0003.jpg",
        "kind": "photo",
        "available": True,
    }


def test_message_text_removes_phone_like_content_and_resolves_wrapped_mentions():
    chat = (
        "13/10/26, 9:00 am - +91 90000 00000: Synthetic authored text\n"
        "13/10/26, 9:01 am - Asha Sharma: Ask \u2068+91 90000 00000\u2069; "
        "model AC-12345 shows E6, quantity 2. Remove +91 90000 00000\n"
    ).encode()

    parsed = parse_chat(chat)

    assert parsed.messages[0].speaker == "Participant 1"
    assert parsed.messages[1].text == "Ask Participant 1; model AC-12345 shows E6, quantity 2. Remove"
    assert "90000" not in parsed.messages[1].text


def test_message_phone_filter_preserves_codes_models_voltage_quantities_and_price():
    chat = (
        "13/10/26, 9:00 am - Asha Sharma: Call +91 90000-00000, 09000000000, or +44 7000 000000; "
        "part EBR41956415; input 220-230 V; batch 4502568/2019; model AC-12345; price ₹12,500"
    ).encode()

    text = parse_chat(chat).messages[0].text

    assert text == (
        "Call , , or ; part EBR41956415; input 220-230 V; batch 4502568/2019; "
        "model AC-12345; price ₹12,500"
    )


@pytest.mark.parametrize(
    ("chat", "platform", "expected"),
    [
        (b"16/10/26, 14:03 - Asha Sharma: Android 24 hour", "android", datetime(2026, 10, 16, 14, 3)),
        (b"[10/16/26, 23:40:05] Dev Kumar: iOS 24 hour", "ios", datetime(2026, 10, 16, 23, 40, 5)),
    ],
)
def test_24_hour_timestamps_preserve_platform_and_proven_date_order(chat, platform, expected):
    parsed = parse_chat(chat)

    assert parsed.platform == platform
    assert parsed.messages[0].timestamp == expected


def test_ambiguous_date_requires_explicit_order():
    chat = b"01/02/26, 9:00 am - Asha Sharma: Synthetic message"

    with pytest.raises(AmbiguousDateOrderError):
        parse_chat(chat)

    day_first = parse_chat(chat, date_order=DateOrder.DAY_FIRST)
    month_first = parse_chat(chat, date_order=DateOrder.MONTH_FIRST)
    assert day_first.messages[0].timestamp == datetime(2026, 2, 1, 9, 0)
    assert month_first.messages[0].timestamp == datetime(2026, 1, 2, 9, 0)


def test_unsafe_attachment_name_is_not_mapped():
    chat = b"13/10/26, 9:00 am - Asha Sharma: ../private.jpg (file attached)"

    parsed = parse_chat(chat, archive_filenames={"../private.jpg"})

    assert parsed.messages[0].attachment is None
    assert parsed.messages[0].text == "../private.jpg (file attached)"
