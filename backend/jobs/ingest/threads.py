"""Topic grouping boundary with deterministic time-gap fallback."""

import logging
from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from typing import Protocol

from jobs.ingest.models import Threads
from models.imports import ThreadMessage

FALLBACK_GAP = timedelta(minutes=30)
FALLBACK_WARNING = "Flash grouping was unavailable or invalid; using deterministic time-gap grouping."
logger = logging.getLogger(__name__)


class ThreadGroupingClient(Protocol):
    async def group_threads(self, messages: list[ThreadMessage]) -> object: ...


def _ordered(messages: Sequence[ThreadMessage]) -> list[ThreadMessage]:
    return [message for _, message in sorted(enumerate(messages), key=lambda item: (item[1].ts, item[0]))]


def fallback_threads(messages: Sequence[ThreadMessage]) -> Threads:
    ordered = _ordered(messages)
    groups: list[list[str]] = []
    previous: ThreadMessage | None = None

    for message in ordered:
        if previous is None or message.ts - previous.ts > FALLBACK_GAP:
            groups.append([])
        groups[-1].append(message.id)
        previous = message

    return Threads(groups=groups)


def _warn_and_fallback(messages: Sequence[ThreadMessage]) -> Threads:
    logger.warning(FALLBACK_WARNING)
    return fallback_threads(messages)


def _valid_groups(groups: Threads, ordered: list[ThreadMessage]) -> bool:
    expected_ids = [message.id for message in ordered]
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError("eligible message ids must be unique")

    received_ids = [message_id for group in groups.groups for message_id in group]
    if any(not group for group in groups.groups) or Counter(received_ids) != Counter(expected_ids):
        return False

    position = {message_id: index for index, message_id in enumerate(expected_ids)}
    return all(
        [position[message_id] for message_id in group]
        == sorted(position[message_id] for message_id in group)
        for group in groups.groups
    )


async def topic_threads(messages: Sequence[ThreadMessage], client: ThreadGroupingClient) -> Threads:
    ordered = _ordered(messages)
    try:
        response = Threads.model_validate(await client.group_threads(ordered))
        if _valid_groups(response, ordered):
            return response
    except Exception:  # noqa: BLE001 — every client or schema failure must use the deterministic fallback
        return _warn_and_fallback(ordered)
    return _warn_and_fallback(ordered)


async def group_thread_messages(
    messages: Sequence[ThreadMessage], client: ThreadGroupingClient
) -> list[list[ThreadMessage]]:
    """Return validated, enriched messages in the shape consumed by T15 import_cards."""

    ordered = _ordered(messages)
    grouping = await topic_threads(ordered, client)
    messages_by_id = {message.id: message for message in ordered}
    position = {message.id: index for index, message in enumerate(ordered)}
    chronological_groups = sorted(grouping.groups, key=lambda group: position[group[0]])
    return [[messages_by_id[message_id] for message_id in group] for group in chronological_groups]
