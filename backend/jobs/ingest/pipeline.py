"""Offline coordinator for the dependency-injected WhatsApp import stages."""

import inspect
import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from jobs.ingest.adapter import EnrichMessage, prepare_thread_messages
from jobs.ingest.cards import Ask, import_cards
from jobs.ingest.parse import AmbiguousDateOrderError, parse_chat
from jobs.ingest.threads import ThreadGroupingClient, group_thread_messages
from models.imports import CardCounts
from models.media import ImportId
from tools.search_fault_cards import Embed

EXPORT_TIMEZONE = ZoneInfo("Asia/Kolkata")
AMBIGUOUS_DATE = "The chat date order could not be determined, so the import was not processed."
PIPELINE_FAILED = "The chat import could not be processed."
logger = logging.getLogger(__name__)


class ImportLifecycle(StrEnum):
    PARSING = "parsing"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    DONE = "done"
    FAILED = "failed"


LifecycleCallback = Callable[[ImportLifecycle], Awaitable[None] | None]


class PipelineResult(CardCounts):
    status: ImportLifecycle
    audio_total: int = 0
    audio_done: int = 0
    threads: int = 0

    @property
    def card_counts(self) -> CardCounts:
        """Keep merged counts available internally without making them a persistence field."""

        return CardCounts.model_validate(self.model_dump(exclude={"status"}))


async def _report(callback: LifecycleCallback, status: ImportLifecycle) -> None:
    reported = callback(status)
    if inspect.isawaitable(reported):
        await reported


def _failed(error: str) -> PipelineResult:
    return PipelineResult(status=ImportLifecycle.FAILED, errors=[error])


async def run_import_pipeline(
    chat_data: bytes,
    *,
    import_id: ImportId,
    archive_filenames: Iterable[str],
    enrich: EnrichMessage,
    thread_client: ThreadGroupingClient,
    ask: Ask,
    embed: Embed,
    store,
    now: datetime,
    on_lifecycle: LifecycleCallback,
) -> PipelineResult:
    """Run the offline import stages; all service boundaries are supplied by the caller."""

    await _report(on_lifecycle, ImportLifecycle.PARSING)
    try:
        parsed = parse_chat(chat_data, archive_filenames=archive_filenames)
    except AmbiguousDateOrderError:
        await _report(on_lifecycle, ImportLifecycle.FAILED)
        return _failed(AMBIGUOUS_DATE)
    except Exception:  # noqa: BLE001 — the result and log must never expose private export details
        logger.error("import parsing failed")
        await _report(on_lifecycle, ImportLifecycle.FAILED)
        return _failed(PIPELINE_FAILED)

    try:
        await _report(on_lifecycle, ImportLifecycle.TRANSCRIBING)
        prepared = await prepare_thread_messages(
            parsed.messages,
            import_id=import_id,
            timezone=EXPORT_TIMEZONE,
            enrich=enrich,
        )
        await _report(on_lifecycle, ImportLifecycle.EXTRACTING)
        threads = await group_thread_messages(prepared.messages, thread_client)
        counts = await import_cards(threads, ask, embed, store, now)
    except Exception:  # noqa: BLE001 — dependency errors may contain private export data
        logger.error("import pipeline failed")
        await _report(on_lifecycle, ImportLifecycle.FAILED)
        return _failed(PIPELINE_FAILED)

    errors = [*prepared.errors, *counts.errors]
    await _report(on_lifecycle, ImportLifecycle.DONE)
    return PipelineResult(
        status=ImportLifecycle.DONE,
        audio_total=sum(message.kind == "voice" for message in prepared.messages),
        audio_done=sum(message.kind == "voice" for message in prepared.messages),
        threads=len(threads),
        cards_created=counts.cards_created,
        cards_merged=counts.cards_merged,
        cards_needing_review=counts.cards_needing_review,
        errors=errors,
    )
