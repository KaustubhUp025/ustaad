"""Pure parser for Android and iOS WhatsApp chat exports."""

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

from jobs.ingest.models import Attachment, ExportMessage, ParsedChat

ANDROID_LINE = re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), "
    r"(?P<time>\d{1,2}:\d{2})(?:[ \u00a0\u202f](?P<ampm>[AaPp][Mm]))? - (?P<body>.*)$"
)
IOS_LINE = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), "
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?)(?:[ \u00a0\u202f](?P<ampm>[AaPp][Mm]))?\] (?P<body>.*)$"
)
AUTHORED_BODY = re.compile(r"^(?P<author>[^:]+):(?P<content>.*)$")
ATTACHMENT_TEXT = re.compile(r"^(?P<filename>.+) \(file attached\)$", re.IGNORECASE)
IOS_ATTACHMENT_TEXT = re.compile(r"^<attached: (?P<filename>.+)>$", re.IGNORECASE)
ISOLATED_MENTION = re.compile(r"\u2068(?P<text>.*?)\u2069")
PHONE_NUMBER = re.compile(r"(?<![\w])(?:\+?91[\s().-]*)?[6-9](?:[\s().-]*\d){9}(?!\w)")
MESSAGE_PHONE_NUMBER = re.compile(
    r"(?<![\w+])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\w)|\+\d[\d\s-]{8,}\d"
)
STRUCTURAL_CONTROLS = str.maketrans("", "", "\u200e\u200f\u2066\u2067\u2068\u2069")
LINE_CONTROLS = str.maketrans("", "", "\u200e\u200f\u2066\u2067")
DELETED_MESSAGES = frozenset({"this message was deleted", "you deleted this message"})


class DateOrder(StrEnum):
    DAY_FIRST = "day_first"
    MONTH_FIRST = "month_first"


class AmbiguousDateOrderError(ValueError):
    """Raised when every date could be interpreted in either supported order."""


@dataclass
class _Record:
    date: str
    time: str
    ampm: str | None
    body: str
    export_index: int
    author: str | None = None
    content: str | None = None


def _line_match(line: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    return pattern.match(line.translate(LINE_CONTROLS))


def _detect_platform(lines: list[str]) -> tuple[str, re.Pattern[str]]:
    android = sum(_line_match(line, ANDROID_LINE) is not None for line in lines)
    ios = sum(_line_match(line, IOS_LINE) is not None for line in lines)
    if android and ios:
        raise ValueError("chat mixes Android and iOS timestamp formats")
    if android:
        return "android", ANDROID_LINE
    if ios:
        return "ios", IOS_LINE
    raise ValueError("chat contains no supported WhatsApp timestamps")


def _records(lines: list[str], pattern: re.Pattern[str]) -> list[_Record]:
    records: list[_Record] = []
    current: _Record | None = None

    for line in lines:
        match = _line_match(line, pattern)
        if match:
            body = match.group("body")
            authored = AUTHORED_BODY.match(body)
            content = authored.group("content") if authored else None
            if content is not None and content.startswith(" "):
                content = content[1:]
            current = _Record(
                date=match.group("date"),
                time=match.group("time"),
                ampm=match.group("ampm"),
                body=body,
                export_index=len(records),
                author=authored.group("author").translate(STRUCTURAL_CONTROLS).strip() if authored else None,
                content=content,
            )
            records.append(current)
        elif current is not None:
            current.body += f"\n{line}"
            if current.content is not None:
                current.content += f"\n{line}"

    return records


def _date_order(records: list[_Record], explicit: DateOrder | None) -> DateOrder:
    evidence: set[DateOrder] = set()
    for record in records:
        first, second, _ = (int(part) for part in record.date.split("/"))
        if first > 12 and second > 12:
            raise ValueError("date has no valid day/month interpretation")
        if first > 12:
            evidence.add(DateOrder.DAY_FIRST)
        elif second > 12:
            evidence.add(DateOrder.MONTH_FIRST)

    if len(evidence) > 1:
        raise ValueError("chat contains conflicting date-order evidence")
    if explicit is not None:
        if evidence and explicit not in evidence:
            raise ValueError("explicit date order conflicts with chat dates")
        return explicit
    if evidence:
        return evidence.pop()
    raise AmbiguousDateOrderError("date order is ambiguous; pass date_order explicitly")


def _timestamp(record: _Record, order: DateOrder) -> datetime:
    first, second, year = (int(part) for part in record.date.split("/"))
    day, month = (first, second) if order is DateOrder.DAY_FIRST else (second, first)
    if year < 100:
        year += 2000
    hour, minute, *seconds = (int(part) for part in record.time.split(":"))
    if record.ampm is not None:
        hour = hour % 12 + (12 if record.ampm.lower() == "pm" else 0)
    return datetime(year, month, day, hour, minute, seconds[0] if seconds else 0)


def _speaker_aliases(records: list[_Record]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    neutral_count = 0
    for record in records:
        if record.author is None or record.author in aliases:
            continue
        without_phone = PHONE_NUMBER.sub("", record.author).strip(" -(),")
        name_tokens = [token.strip(" -(),") for token in without_phone.split()]
        first_name = next((token for token in name_tokens if any(character.isalpha() for character in token)), None)
        if first_name:
            aliases[record.author] = first_name
        else:
            neutral_count += 1
            aliases[record.author] = f"Participant {neutral_count}"
    return aliases


def _normalized_content(content: str, aliases: dict[str, str]) -> str:
    def mention_text(match: re.Match[str]) -> str:
        text = match.group("text").translate(STRUCTURAL_CONTROLS).strip()
        return aliases.get(text, text)

    normalized = ISOLATED_MENTION.sub(mention_text, content).translate(STRUCTURAL_CONTROLS)
    without_phones = MESSAGE_PHONE_NUMBER.sub("", normalized)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in without_phones.split("\n")]
    return "\n".join(lines)


def _safe_archive_basenames(filenames: Iterable[str]) -> set[str]:
    basenames: list[str] = []
    for filename in filenames:
        path = PurePosixPath(filename)
        if path.is_absolute() or ".." in path.parts or not path.name:
            continue
        basenames.append(path.name)
    counts = Counter(basenames)
    return {name for name, count in counts.items() if count == 1}


def _attachment(content: str, available_names: set[str]) -> Attachment | None:
    match = ATTACHMENT_TEXT.fullmatch(content) or IOS_ATTACHMENT_TEXT.fullmatch(content)
    if not match:
        return None
    filename = match.group("filename")
    if PurePosixPath(filename).name != filename or "\\" in filename or filename in {".", ".."}:
        return None
    extension = PurePosixPath(filename).suffix.lower()
    kind = {
        ".ogg": "audio",
        ".opus": "audio",
        ".jpg": "photo",
        ".jpeg": "photo",
        ".png": "photo",
        ".mp4": "video",
    }.get(extension, "file")
    return Attachment(filename=filename, kind=kind, available=filename in available_names)


def parse_chat(
    data: bytes,
    *,
    archive_filenames: Iterable[str] = (),
    date_order: DateOrder | str | None = None,
) -> ParsedChat:
    explicit_order = DateOrder(date_order) if date_order is not None else None
    text = data.decode("utf-8-sig")
    lines = text.splitlines()
    platform, pattern = _detect_platform(lines)
    records = _records(lines, pattern)
    resolved_order = _date_order(records, explicit_order)
    aliases = _speaker_aliases(records)
    available_names = _safe_archive_basenames(archive_filenames)
    parsed: list[tuple[datetime, int, str, str, Attachment | None]] = []

    for record in records:
        if record.author is None or record.content is None:
            continue
        content = _normalized_content(record.content, aliases)
        if content.strip().lower() in DELETED_MESSAGES:
            continue
        attachment = _attachment(content, available_names)
        parsed.append(
            (
                _timestamp(record, resolved_order),
                record.export_index,
                aliases[record.author],
                "" if attachment else content,
                attachment,
            )
        )

    parsed.sort(key=lambda message: (message[0], message[1]))
    messages = [
        ExportMessage(
            id=f"m{index}",
            timestamp=timestamp,
            export_index=export_index,
            speaker=speaker,
            text=content,
            attachment=attachment,
        )
        for index, (timestamp, export_index, speaker, content, attachment) in enumerate(parsed, start=1)
    ]
    return ParsedChat(platform=platform, date_order=resolved_order, messages=messages)
