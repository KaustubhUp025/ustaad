"""Dependency-injected media enrichment for parsed WhatsApp attachments."""

from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from jobs.ingest.adapter import EnrichmentFailed
from jobs.ingest.models import ExportMessage, MessageEnrichment
from models.media import ImportId, SafeFilename

ConvertAudio = Callable[[Path, Path], Awaitable[None]]
UploadAudio = Callable[[Path, str], Awaitable[str]]
TranscribeAudio = Callable[[Path], Awaitable[str]]
DescribePhoto = Callable[[Path], Awaitable[str]]

IMPORT_ID_ADAPTER = TypeAdapter(ImportId)
SAFE_FILENAME_ADAPTER = TypeAdapter(SafeFilename)


def _safe_media_by_basename(archive_files: Sequence[Path]) -> dict[str, Path]:
    counts = Counter(path.name for path in archive_files)
    matched: dict[str, Path] = {}
    for path in archive_files:
        try:
            basename = SAFE_FILENAME_ADAPTER.validate_python(path.name)
        except ValidationError:
            continue
        if counts[basename] == 1:
            matched[basename] = path
    return matched


def create_media_enricher(
    *,
    import_id: ImportId,
    media_bucket: str,
    archive_files: Sequence[Path],
    derived_directory: Path,
    converter: ConvertAudio,
    uploader: UploadAudio,
    transcriber: TranscribeAudio,
    describer: DescribePhoto,
) -> Callable[[ExportMessage], Awaitable[MessageEnrichment]]:
    """Build the per-message callable consumed by ``prepare_thread_messages``."""

    validated_import_id = IMPORT_ID_ADAPTER.validate_python(import_id)
    media_by_basename = _safe_media_by_basename(archive_files)

    async def enrich(message: ExportMessage) -> MessageEnrichment:
        attachment = message.attachment
        if attachment is None or attachment.kind not in {"audio", "photo"}:
            raise ValueError("message has no enrichable attachment")
        if not attachment.available:
            raise ValueError("attachment is unavailable")

        source = media_by_basename.get(attachment.filename)
        if source is None:
            raise ValueError("attachment has no unique safe basename match")

        if attachment.kind == "photo":
            return MessageEnrichment(text=await describer(source))

        derived_directory.mkdir(parents=True, exist_ok=True)
        flac = derived_directory / f"{message.id}.flac"
        destination_uri = f"gs://{media_bucket}/imports/{validated_import_id}/derived/{message.id}.flac"
        await converter(source, flac)
        transcript = await transcriber(flac)
        try:
            uploaded_uri = await uploader(flac, destination_uri)
            if uploaded_uri != destination_uri:
                raise ValueError("uploader returned an unexpected destination")
        except Exception:  # noqa: BLE001 — preserve the transcript; adapter emits the fixed safe error
            raise EnrichmentFailed(MessageEnrichment(text=transcript)) from None
        return MessageEnrichment(text=transcript, audio_uri=uploaded_uri)

    return enrich
