"""Adapt raw export messages to the shared T15 thread input model."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import tzinfo
from typing import Literal

from pydantic import TypeAdapter

from jobs.ingest.models import ExportMessage, MessageEnrichment, PreparationResult
from models.imports import ThreadMessage
from models.media import ImportId

IMPORT_ID_ADAPTER = TypeAdapter(ImportId)
logger = logging.getLogger(__name__)

# Goes to imports.errors[] and the dashboard, so it is fixed text: never exception text, ids, URIs or chat content.
ENRICHMENT_FAILED = "One chat attachment could not be read, so it was kept without enrichment."
EnrichMessage = Callable[[ExportMessage], Awaitable[MessageEnrichment]]


def _kind(message: ExportMessage) -> Literal["text", "voice", "photo"]:
    if message.attachment is None:
        return "text"
    if message.attachment.kind == "audio":
        return "voice"
    if message.attachment.kind == "photo":
        return "photo"
    raise ValueError("T15 accepts only text, voice and photo messages")


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

        enriched_text = message.text
        if kind != "text" and enrichment is not None and enrichment.text is not None:
            enriched_text = enrichment.text

        adapted.append(
            ThreadMessage(
                id=f"{validated_import_id}:{message.id}",
                speaker=message.speaker,
                ts=message.timestamp.replace(tzinfo=timezone),
                kind=kind,
                text=enriched_text,
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
    for message in messages:
        if message.attachment is None or message.attachment.kind not in {"audio", "photo"}:
            continue
        try:
            enrichments[message.id] = await enrich(message)
        except Exception as error:
            logger.error("message enrichment failed", exc_info=error)
            enrichments[message.id] = MessageEnrichment()
            errors.append(ENRICHMENT_FAILED)

    return PreparationResult(
        messages=to_thread_messages(
            messages,
            import_id=import_id,
            timezone=timezone,
            enrichments=enrichments,
        ),
        errors=errors,
    )
