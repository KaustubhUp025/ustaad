"""Memory Bank for one worker (SPEC §6 Memory, S3): his soft facts are read at session start and his words saved at
session end. ADK's PreloadMemoryTool searches with the typed user text, which a Live voice session never has, and
Live keeps speech as transcriptions rather than content, so both ends are done here."""

import logging

from google.adk.events import Event
from google.adk.memory import BaseMemoryService
from google.genai import types

logger = logging.getLogger(__name__)

APP = "ustaad"
QUERY = "Which language does he prefer, and which repairs or parts is he weak at or still learning?"


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
    """Saves what both speakers said in the session, from its final transcriptions."""
    said = [
        Event(author=author, content=types.Content(role=role, parts=[types.Part(text=line.text)]))
        for event in events
        for author, role, line in (
            ("user", "user", event.input_transcription),
            ("ustaad", "model", event.output_transcription),
        )
        if line and line.text
    ]
    if not said:
        return
    try:
        await memory.add_events_to_memory(app_name=APP, user_id=user_id, events=said)
    except Exception:
        logger.warning("memory save failed", exc_info=True)
