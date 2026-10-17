"""Concrete, retry-safe entry point for the WhatsApp import Cloud Run Job."""

import asyncio
import logging
import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from google.cloud import firestore
from pydantic import TypeAdapter, ValidationError

from clients.audio import to_flac
from clients.firestore import CardStore, ImportStore
from clients.gemini import ask_json, describe_import_photo, embed, transcribe_import_audio
from clients.storage import ImportStorageClient
from jobs.ingest.adapter import ENRICHMENT_FAILED
from jobs.ingest.cards import EXTRACTION_FAILED, Ask
from jobs.ingest.media import ConvertAudio, DescribePhoto, TranscribeAudio, create_media_enricher
from jobs.ingest.pipeline import AMBIGUOUS_DATE, PIPELINE_FAILED, ImportLifecycle, run_import_pipeline
from jobs.ingest.threads import FlashThreadGroupingClient, ThreadGroupingClient
from models.media import ImportId

EXPECTED_DATABASE = "(default)"
EXPECTED_MEDIA_BUCKET = "ustaad101-media"
PREFLIGHT_FAILED = "Import configuration is not allowed."
IMPORT_FAILED = "The chat import could not be processed."
SAFE_IMPORT_ERRORS = frozenset(
    {AMBIGUOUS_DATE, PIPELINE_FAILED, ENRICHMENT_FAILED, EXTRACTION_FAILED, IMPORT_FAILED}
)
logger = logging.getLogger(__name__)
IMPORT_ID_ADAPTER = TypeAdapter(ImportId)


@dataclass(frozen=True)
class PreflightResult:
    import_id: str | None = None
    media_bucket: str | None = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.error is None


def preflight(env: Mapping[str, str]) -> PreflightResult:
    import_id = env.get("IMPORT_ID")
    if (
        env.get("FIRESTORE_DB") != EXPECTED_DATABASE
        or env.get("MEDIA_BUCKET") != EXPECTED_MEDIA_BUCKET
        or not import_id
    ):
        return PreflightResult(error=PREFLIGHT_FAILED)
    try:
        import_id = IMPORT_ID_ADAPTER.validate_python(import_id)
    except ValidationError:
        return PreflightResult(error=PREFLIGHT_FAILED)
    return PreflightResult(import_id=import_id, media_bucket=EXPECTED_MEDIA_BUCKET)


def _read_archive(data: bytes):
    from jobs.ingest.archive import read_whatsapp_zip

    return read_whatsapp_zip(data)


def materialize_root_attachments(
    archive_bytes: bytes, basenames: Iterable[str], directory: Path
) -> list[Path]:
    paths: list[Path] = []
    with ZipFile(BytesIO(archive_bytes)) as archive:
        for basename in basenames:
            destination = directory / basename
            destination.write_bytes(archive.read(basename))
            paths.append(destination)
    return paths


async def convert_to_flac(source: Path, destination: Path) -> None:
    destination.write_bytes(await to_flac(source.read_bytes()))


@dataclass
class ImportJobDependencies:
    imports: object
    storage: object | None = None
    cards: object | None = None
    read_archive: Callable[[bytes], object] | None = None
    materialize: Callable[[bytes, Iterable[str], Path], list[Path]] | None = None
    converter: ConvertAudio | None = None
    transcriber: TranscribeAudio | None = None
    describer: DescribePhoto | None = None
    thread_client: ThreadGroupingClient | None = None
    ask: Ask | None = None
    embed: Callable | None = None
    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    workspace: Path | None = None

    @classmethod
    def unused_for_skip(cls, *, imports, workspace: Path) -> "ImportJobDependencies":
        return cls(imports=imports, workspace=workspace)


def _fixed_errors(existing: list[str], new: list[str]) -> list[str]:
    return list(
        dict.fromkeys(
            error for error in [*existing, *new] if isinstance(error, str) and error in SAFE_IMPORT_ERRORS
        )
    )


async def run_ingest_job(import_id: str, media_bucket: str, deps: ImportJobDependencies) -> bool:
    record = deps.imports.load(import_id)
    if record is None:
        logger.error("import job failed")
        return False
    if record["status"] == "done":
        return True

    workspace = deps.workspace / import_id
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        archive_bytes = deps.storage.load_archive(import_id)
        intake = deps.read_archive(archive_bytes)
        archive_files = deps.materialize(archive_bytes, intake.attachment_basenames, workspace)
        enricher = create_media_enricher(
            import_id=import_id,
            media_bucket=media_bucket,
            archive_files=archive_files,
            derived_directory=workspace / "derived",
            converter=deps.converter,
            uploader=deps.storage.upload_derived,
            transcriber=deps.transcriber,
            describer=deps.describer,
        )

        async def lifecycle(status: ImportLifecycle) -> None:
            if status in {
                ImportLifecycle.PARSING,
                ImportLifecycle.TRANSCRIBING,
                ImportLifecycle.EXTRACTING,
            }:
                fields = {"status": status.value}
                if status is ImportLifecycle.PARSING:
                    fields |= {
                        "errors": [],
                        "files_total": 1 + len(intake.attachment_basenames),
                        "started_at": deps.now(),
                    }
                deps.imports.update(import_id, **fields)

        result = await run_import_pipeline(
            intake.chat_bytes,
            import_id=import_id,
            archive_filenames=intake.attachment_basenames,
            enrich=enricher,
            thread_client=deps.thread_client,
            ask=deps.ask,
            embed=deps.embed,
            store=deps.cards,
            now=deps.now(),
            on_lifecycle=lifecycle,
        )
    except Exception:  # noqa: BLE001 — source data and service errors must never enter logs or Firestore
        logger.error("import job failed")
        deps.imports.update(
            import_id,
            status="failed",
            errors=_fixed_errors([], [IMPORT_FAILED]),
            finished_at=deps.now(),
        )
        return False

    errors = _fixed_errors([], result.errors)
    if result.status is ImportLifecycle.FAILED:
        deps.imports.update(import_id, status="failed", errors=errors, finished_at=deps.now())
        return False
    deps.imports.update(
        import_id,
        status="done",
        audio_total=result.audio_total,
        audio_done=result.audio_done,
        threads=result.threads,
        cards_created=result.cards_created,
        cards_needing_review=result.cards_needing_review,
        errors=errors,
        finished_at=deps.now(),
    )
    return True


def _concrete_dependencies(database: str, bucket: str, workspace: Path) -> ImportJobDependencies:
    db = firestore.Client(database=database)
    return ImportJobDependencies(
        imports=ImportStore(db),
        storage=ImportStorageClient(bucket),
        cards=CardStore(db),
        read_archive=_read_archive,
        materialize=materialize_root_attachments,
        converter=convert_to_flac,
        transcriber=transcribe_import_audio,
        describer=describe_import_photo,
        thread_client=FlashThreadGroupingClient(),
        ask=ask_json,
        embed=embed,
        workspace=workspace,
    )


def main() -> int:
    config = preflight(os.environ)
    if not config:
        logger.error(PREFLIGHT_FAILED)
        return 2
    with TemporaryDirectory(prefix="ustaad-import-") as directory:
        dependencies = _concrete_dependencies(EXPECTED_DATABASE, config.media_bucket, Path(directory))
        return 0 if asyncio.run(run_ingest_job(config.import_id, config.media_bucket, dependencies)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
