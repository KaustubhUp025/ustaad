import asyncio
from datetime import UTC, datetime

from google.adk.events import Event
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types

from agent.memory import memory_user, recall, remember
from app.session import issue


class FakeMemoryBank:
    """Keeps each user's saved lines and hands them all back as facts, like Memory Bank scoped by user id."""

    def __init__(self):
        self.saved: dict[str, list[str]] = {}

    async def add_events_to_memory(self, *, app_name, user_id, events, **_):
        self.saved.setdefault(user_id, []).extend(
            f"{e.author}: {e.content.parts[0].text}" for e in events
        )

    async def search_memory(self, *, app_name, user_id, query):
        return SearchMemoryResponse(
            memories=[
                MemoryEntry(author="user", content=types.Content(role="user", parts=[types.Part(text=fact)]))
                for fact in self.saved.get(user_id, [])
            ]
        )


def spoken(who, text):
    field = "input_transcription" if who == "user" else "output_transcription"
    return Event(author="ustaad", **{field: types.Transcription(text=text, finished=True)})


def test_a_second_session_recalls_the_language_and_weak_area_from_the_first():
    bank = FakeMemoryBank()
    first = [
        spoken("user", "Mujhse Hindi mein baat karo"),
        spoken("ustaad", "Theek hai."),
        spoken("user", "Inverter PCB mein mujhe dikkat hoti hai"),
        Event(author="ustaad", turn_complete=True),
    ]
    asyncio.run(remember(bank, "dev:w_hi_demo", first))
    summary = asyncio.run(recall(bank, "dev:w_hi_demo"))
    assert "Hindi" in summary and "Inverter PCB" in summary


def test_memories_stay_with_their_worker_and_database():
    bank = FakeMemoryBank()
    asyncio.run(remember(bank, "dev:w_hi_demo", [spoken("user", "Inverter PCB weak hai")]))
    assert asyncio.run(recall(bank, "demo:w_hi_demo")) is None
    assert asyncio.run(recall(bank, "dev:w_te_demo")) is None


def test_a_session_with_nothing_said_saves_nothing():
    bank = FakeMemoryBank()
    asyncio.run(remember(bank, "dev:w_hi_demo", [Event(author="ustaad", turn_complete=True)]))
    assert bank.saved == {}


def test_two_demo_visitors_on_w_hi_demo_never_see_each_others_memories():
    now = datetime.now(UTC)
    judge_a = memory_user("demo", "w_hi_demo", issue("w_hi_demo", now))
    judge_b = memory_user("demo", "w_hi_demo", issue("w_hi_demo", now))
    bank = FakeMemoryBank()
    asyncio.run(remember(bank, judge_a, [spoken("user", "Mera naam Test Judge hai, inverter PCB weak hai")]))
    assert asyncio.run(recall(bank, judge_b)) is None
    assert "inverter PCB" in asyncio.run(recall(bank, judge_a))


def test_the_same_visit_keeps_its_memory_across_sessions():
    token = issue("w_hi_demo", datetime.now(UTC))
    assert memory_user("demo", "w_hi_demo", token) == memory_user("demo", "w_hi_demo", token)
    assert memory_user("dev", "w_hi_demo", token) != memory_user("demo", "w_hi_demo", token)
