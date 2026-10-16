"""Adapt raw export messages to the shared T15 thread input model."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import tzinfo
from pathlib import PurePath
from typing import Literal

from pydantic import TypeAdapter

from jobs.ingest.models import ExportMessage, MessageEnrichment, PreparationResult
from models.imports import ThreadMessage
from models.media import ImportId

IMPORT_ID_ADAPTER = TypeAdapter(ImportId)
logger = logging.getLogger(__name__)

# Goes to imports.errors[] and the dashboard, so it is fixed text: never exception text, ids, URIs or chat content.
ENRICHMENT_FAILED = "One chat attachment could not be read, so it was kept without enrichment."
ENRICH_PARALLEL = 8
EnrichMessage = Callable[[ExportMessage], Awaitable[MessageEnrichment]]


def _kind(message: ExportMessage) -> Literal["text", "voice", "photo"]:
    if message.attachment is None:
        return "text"
    if message.attachment.kind == "audio":
        return "voice"
    if message.attachment.kind == "photo":
        return "photo"
    return "text"


def _text(message: ExportMessage, kind: Literal["text", "voice", "photo"], enrichment: MessageEnrichment | None) -> str:
    if kind != "text" and enrichment is not None and enrichment.text is not None:
        return enrichment.text
    if message.text:
        return message.text
    if message.attachment is None:
        return ""
    if message.attachment.kind == "video":
        return "(video)"
    if PurePath(message.attachment.filename).suffix.lower() == ".webp":
        return "(sticker)"
    if message.attachment.kind == "file":
        return "(attachment)"
    return ""


def to_thread_messages(
    messages: list[ExportMessage],
    *,
    import_id: ImportId,
    timezone: tzinfo,
    enrichments: Mapping[str, MessageEnrichment] | None = None,
) -> list[ThreadMessage]:
    if timezone is None:
        raise ValueError("the export timezone is required")

    validated_import_id = IMPORT_ID_ADAPTER.validate_python(import_id)
    supplied_enrichments = enrichments or {}
    ordered = sorted(messages, key=lambda message: (message.timestamp, message.export_index))
    adapted: list[ThreadMessage] = []
    for message in ordered:
        kind = _kind(message)
        enrichment = supplied_enrichments.get(message.id)
        if enrichment is not None and enrichment.audio_uri is not None and kind != "voice":
            raise ValueError("audio_uri enrichment is valid only for voice messages")

        adapted.append(
            ThreadMessage(
                id=f"{validated_import_id}:{message.id}",
                speaker=message.speaker,
                ts=message.timestamp.replace(tzinfo=timezone),
                kind=kind,
                text=_text(message, kind, enrichment),
                audio_uri=enrichment.audio_uri if kind == "voice" and enrichment is not None else None,
            )
        )
    return adapted


async def prepare_thread_messages(
    messages: list[ExportMessage],
    *,
    import_id: ImportId,
    timezone: tzinfo,
    enrich: EnrichMessage,
) -> PreparationResult:
    """Enrich media offline through an injected callable, then adapt once for grouping and T15."""

    enrichments: dict[str, MessageEnrichment] = {}
    errors: list[str] = []
    media_messages = [
        message
        for message in messages
        if message.attachment is not None and message.attachment.kind in {"audio", "photo"}
    ]
    limit = asyncio.Semaphore(ENRICH_PARALLEL)

    async def enrich_one(message: ExportMessage) -> MessageEnrichment:
        try:
            async with limit:
                return await enrich(message)
        except Exception:  # noqa: BLE001 — per-media failures are reduced to one fixed safe import error
            logger.error("message enrichment failed")
            errors.append(ENRICHMENT_FAILED)
            return MessageEnrichment()

    results = await asyncio.gather(*(enrich_one(message) for message in media_messages))
    enrichments.update(
        (message.id, enrichment) for message, enrichment in zip(media_messages, results, strict=True)
    )

    return PreparationResult(
        messages=to_thread_messages(
            messages,
            import_id=import_id,
            timezone=timezone,
            enrichments=enrichments,
        ),
        errors=errors,
    )
