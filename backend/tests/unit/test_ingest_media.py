import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jobs.ingest.adapter import ENRICHMENT_FAILED, prepare_thread_messages
from jobs.ingest.media import create_media_enricher
from jobs.ingest.models import Attachment, ExportMessage

INDIA = ZoneInfo("Asia/Kolkata")
MEDIA_BUCKET = "ustaad101-media"


def media_message(
    message_id: str,
    *,
    filename: str,
    kind: str,
    available: bool = True,
    minute: int = 0,
) -> ExportMessage:
    return ExportMessage(
        id=message_id,
        speaker="TechA",
        timestamp=datetime(2026, 10, 16, 9, minute),
        text="",
        attachment=Attachment(filename=filename, kind=kind, available=available),
        export_index=int(message_id[1:]) - 1,
    )


class FakeMediaDependencies:
    def __init__(self) -> None:
        self.convert_calls: list[tuple[Path, Path]] = []
        self.upload_calls: list[tuple[Path, str]] = []
        self.transcribe_calls: list[Path] = []
        self.describe_calls: list[Path] = []

    async def convert(self, source: Path, destination: Path) -> None:
        self.convert_calls.append((source, destination))

    async def upload(self, source: Path, destination_uri: str) -> str:
        self.upload_calls.append((source, destination_uri))
        return destination_uri

    async def transcribe(self, source: Path) -> str:
        self.transcribe_calls.append(source)
        return "synthetic transcript"

    async def describe(self, source: Path) -> str:
        self.describe_calls.append(source)
        return "Synthetic panel photo."


async def test_voice_converts_to_flac_uploads_exact_destination_and_transcribes(tmp_path):
    source = tmp_path / "voice.opus"
    source.touch()
    derived = tmp_path / "derived"
    fake = FakeMediaDependencies()
    enrich = create_media_enricher(
        import_id="i_media",
        media_bucket=MEDIA_BUCKET,
        archive_files=[source],
        derived_directory=derived,
        converter=fake.convert,
        uploader=fake.upload,
        transcriber=fake.transcribe,
        describer=fake.describe,
    )

    result = await prepare_thread_messages(
        [media_message("m1", filename="voice.opus", kind="audio")],
        import_id="i_media",
        timezone=INDIA,
        enrich=enrich,
    )

    flac = derived / "m1.flac"
    uri = "gs://ustaad101-media/imports/i_media/derived/m1.flac"
    assert fake.convert_calls == [(source, flac)]
    assert fake.transcribe_calls == [flac]
    assert fake.upload_calls == [(flac, uri)]
    assert result.messages[0].text == "synthetic transcript"
    assert result.messages[0].audio_uri == uri
    assert result.errors == []


async def test_photo_uses_exact_safe_basename_and_description(tmp_path):
    wanted = tmp_path / "panel.jpg"
    wanted.touch()
    other = tmp_path / "panel-extra.jpg"
    other.touch()
    fake = FakeMediaDependencies()
    enrich = create_media_enricher(
        import_id="i_photo",
        media_bucket=MEDIA_BUCKET,
        archive_files=[other, wanted],
        derived_directory=tmp_path / "derived",
        converter=fake.convert,
        uploader=fake.upload,
        transcriber=fake.transcribe,
        describer=fake.describe,
    )

    result = await prepare_thread_messages(
        [media_message("m1", filename="panel.jpg", kind="photo")],
        import_id="i_photo",
        timezone=INDIA,
        enrich=enrich,
    )

    assert fake.describe_calls == [wanted]
    assert result.messages[0].text == "Synthetic panel photo."
    assert result.messages[0].audio_uri is None
    assert result.errors == []


async def test_missing_unavailable_duplicate_and_unsafe_media_do_not_match(tmp_path):
    first = tmp_path / "one" / "same.jpg"
    second = tmp_path / "two" / "same.jpg"
    first.parent.mkdir()
    second.parent.mkdir()
    first.touch()
    second.touch()
    unsafe = tmp_path / "bad name.jpg"
    unsafe.touch()
    fake = FakeMediaDependencies()
    enrich = create_media_enricher(
        import_id="i_missing",
        media_bucket=MEDIA_BUCKET,
        archive_files=[first, second, unsafe],
        derived_directory=tmp_path / "derived",
        converter=fake.convert,
        uploader=fake.upload,
        transcriber=fake.transcribe,
        describer=fake.describe,
    )
    messages = [
        media_message("m1", filename="same.jpg", kind="photo"),
        media_message("m2", filename="absent.jpg", kind="photo", minute=1),
        media_message("m3", filename="bad name.jpg", kind="photo", minute=2),
        media_message("m4", filename="unavailable.jpg", kind="photo", available=False, minute=3),
    ]

    result = await prepare_thread_messages(
        messages,
        import_id="i_missing",
        timezone=INDIA,
        enrich=enrich,
    )

    assert [(message.text, message.audio_uri) for message in result.messages] == [("", None)] * 4
    assert result.errors == [ENRICHMENT_FAILED] * 4
    assert fake.describe_calls == []


async def test_dependency_failure_and_wrong_upload_uri_return_only_safe_errors(tmp_path, caplog):
    voice = tmp_path / "voice.opus"
    voice.touch()
    photo = tmp_path / "photo.jpg"
    photo.touch()
    fake = FakeMediaDependencies()

    async def leaking_transcriber(source: Path) -> str:
        raise RuntimeError(
            f"filename={source} token=SYNTHETIC_TOKEN url=https://invalid.example/private "
            "phone=SYNTHETIC_PHONE content=SYNTHETIC_CHAT"
        )

    async def wrong_uri(source: Path, destination_uri: str) -> str:
        return "gs://wrong-bucket/private-token.flac"

    enrich = create_media_enricher(
        import_id="i_errors",
        media_bucket=MEDIA_BUCKET,
        archive_files=[voice, photo],
        derived_directory=tmp_path / "derived",
        converter=fake.convert,
        uploader=wrong_uri,
        transcriber=leaking_transcriber,
        describer=fake.describe,
    )
    result = await prepare_thread_messages(
        [
            media_message("m1", filename="voice.opus", kind="audio"),
            media_message("m2", filename="photo.jpg", kind="photo", minute=1),
        ],
        import_id="i_errors",
        timezone=INDIA,
        enrich=enrich,
    )

    assert result.errors == [ENRICHMENT_FAILED]
    assert [(message.kind, message.text, message.audio_uri) for message in result.messages] == [
        ("voice", "", None),
        ("photo", "Synthetic panel photo.", None),
    ]
    exposed = " ".join(result.errors) + caplog.text
    for secret in (
        "voice.opus",
        "SYNTHETIC_TOKEN",
        "invalid.example",
        "SYNTHETIC_PHONE",
        "SYNTHETIC_CHAT",
        "RuntimeError",
    ):
        assert secret not in exposed

    safe_fake = FakeMediaDependencies()
    enrich_wrong_upload = create_media_enricher(
        import_id="i_errors",
        media_bucket=MEDIA_BUCKET,
        archive_files=[voice],
        derived_directory=tmp_path / "derived",
        converter=safe_fake.convert,
        uploader=wrong_uri,
        transcriber=safe_fake.transcribe,
        describer=safe_fake.describe,
    )
    wrong_upload_result = await prepare_thread_messages(
        [media_message("m1", filename="voice.opus", kind="audio")],
        import_id="i_errors",
        timezone=INDIA,
        enrich=enrich_wrong_upload,
    )
    assert wrong_upload_result.errors == [ENRICHMENT_FAILED]
    assert wrong_upload_result.messages[0].audio_uri is None


async def test_enrichment_caps_concurrency_at_eight_and_preserves_output_order(tmp_path):
    active = 0
    maximum_active = 0
    completions: list[str] = []
    messages: list[ExportMessage] = []
    paths: list[Path] = []
    for index in range(1, 13):
        path = tmp_path / f"photo-{index}.jpg"
        path.touch()
        paths.append(path)
        messages.append(media_message(f"m{index}", filename=path.name, kind="photo", minute=index))

    async def describe_out_of_order(source: Path) -> str:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        index = int(source.stem.split("-")[1])
        await asyncio.sleep((13 - index) / 1000)
        completions.append(source.name)
        active -= 1
        return f"description-{index}"

    fake = FakeMediaDependencies()
    enrich = create_media_enricher(
        import_id="i_parallel",
        media_bucket=MEDIA_BUCKET,
        archive_files=paths,
        derived_directory=tmp_path / "derived",
        converter=fake.convert,
        uploader=fake.upload,
        transcriber=fake.transcribe,
        describer=describe_out_of_order,
    )
    result = await prepare_thread_messages(
        list(reversed(messages)),
        import_id="i_parallel",
        timezone=INDIA,
        enrich=enrich,
    )

    assert maximum_active == 8
    assert completions != [path.name for path in paths]
    assert [message.id for message in result.messages] == [f"i_parallel:m{index}" for index in range(1, 13)]
    assert [message.text for message in result.messages] == [f"description-{index}" for index in range(1, 13)]
