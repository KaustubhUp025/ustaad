"""Memory Bank for one worker (SPEC §6 Memory, S3): his soft facts are read at session start and his words saved at
session end. ADK's PreloadMemoryTool searches with the typed user text, which a Live voice session never has, and
Live keeps speech as transcriptions rather than content, so both ends are done here."""

import hashlib
import logging

from google.adk.events import Event
from google.adk.memory import BaseMemoryService
from google.genai import types

logger = logging.getLogger(__name__)

APP = "ustaad"
QUERY = "Which language does he prefer, and which repairs or parts is he weak at or still learning?"


def memory_user(db: str, worker_id: str, token: str) -> str:
    """Whose memories these are: one demo visit (its session token), on one worker and database. Judges share the
    seeded demo workers, so a worker id alone would carry one judge's words into another judge's session."""
    return f"{db}:{worker_id}:{hashlib.sha256(token.encode()).hexdigest()[:16]}"


async def recall(memory: BaseMemoryService, user_id: str) -> str | None:
    """The worker's remembered facts, one per line, for the instruction's `{memory_summary?}`."""
    # Memory is a soft extra: a Memory Bank failure must not cost him the voice session.
    try:
        found = await memory.search_memory(app_name=APP, user_id=user_id, query=QUERY)
    except Exception:
        logger.warning("memory recall failed", exc_info=True)
        return None
    facts = [part.text for entry in found.memories for part in entry.content.parts or [] if part.text]
    return "\n".join(facts) or None


async def remember(memory: BaseMemoryService, user_id: str, events: list[Event]) -> None:
    """Saves what was said in the session: both speakers' final transcriptions and anything he typed."""
    said = [
        Event(author=author, content=types.Content(role=role, parts=[types.Part(text=text)]))
        for event in events
        for author, role, text in (
            ("user", "user", event.input_transcription and event.input_transcription.text),
            ("ustaad", "model", event.output_transcription and event.output_transcription.text),
            ("user", "user", _typed(event)),
        )
        if text
    ]
    if not said:
        return
    try:
        # wait_for_completion takes ADK's generate path: its default ingest path sends the request from a background
        # task after the client is closed, so nothing was saved (ADK 2.11, Oct 18).
        await memory.add_events_to_memory(
            app_name=APP, user_id=user_id, events=said, custom_metadata={"wait_for_completion": True}
        )
    except Exception:
        logger.warning("memory save failed", exc_info=True)


def _typed(event: Event) -> str | None:
    if event.author != "user" or not event.content:
        return None
    return " ".join(part.text for part in event.content.parts or [] if part.text) or None
