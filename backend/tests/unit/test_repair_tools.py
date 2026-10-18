"""The repair tools as the Live agent calls them (agent/repair_tools.py)."""

import asyncio

from agent.media_tools import MediaDesk
from agent.repair_tools import repair_tools
from models.ws import MediaRequest, SafetyGate
from tests.unit.test_request_media import FakeJobs, FakeQueue, Phone, context


class CardlessJobs(FakeJobs):
    def fault_cards(self, ids):
        return []


async def test_a_repair_whose_first_step_is_gated_shows_the_gate_at_once():
    # Phone test (Oct 17): Ustaad said "supply band kariye" but never called next_step, so no gate reached the phone.
    desk = MediaDesk("j_1", "media")
    phone = Phone()
    desk.attach(phone.send, FakeQueue(), "hi")
    start_repair = repair_tools(CardlessJobs(), desk)[0]
    step = {"instruction": "Test general step", "summary_en": "Test general step"}
    out = start_repair.func(context(), steps=[step])
    await asyncio.gather(*desk.tasks)
    assert out["status"] == "STARTED"
    assert [type(f) for f in phone.frames] == [SafetyGate, MediaRequest]
    assert phone.of(SafetyGate)[0].gate_id == "G_MAINS_OFF"


def test_proposed_steps_are_written_in_the_reply_language():
    # Phone test (Oct 18): in an English session Ustaad wrote the steps in Hindi ("his language"), then said the
    # handed-out step in Hindi after the MCB gate passed.
    from agent.ustaad import INSTRUCTION

    start_repair = repair_tools(CardlessJobs(), MediaDesk("j_1", "media"))[0]
    for text in (start_repair.func.__doc__, INSTRUCTION):
        assert "`instruction` in the reply language" in " ".join(text.split())
