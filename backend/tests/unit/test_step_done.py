"""step_done (ws-events.md, M5): his "done" tap on step card `n` hands out what next_step would, through the same
gate-checked next_step, and Ustaad is told what the phone now shows. Only a tap on the last step handed out counts;
a stale or repeated tap changes nothing and tells no one. No model is called."""

import asyncio

import pytest

from models.repair import RepairJob, RepairStep
from models.ws import MediaRequest, SafetyGate, StepCard
from tests.unit.test_request_media import session
from tools.gates import EVIDENCE

# A card-sourced job: an unsourced (general) one has the mains-off gate before its first step (SAFETY.md).
NOTE = {"kind": "whatsapp_voice", "label": "Ramesh", "audio_uri": None, "doc": None, "page": None}


def step(n: int, hazard="none", english=None) -> RepairStep:
    return RepairStep(n=n, instruction=f"Step {n} karo", instruction_en=english, hazard=hazard, source=NOTE)


def job(*steps: RepairStep, handed_out: int = 1) -> RepairJob:
    return RepairJob(job_id="j_1", steps=list(steps), current_step=handed_out)


async def test_done_on_the_current_step_hands_out_the_next_and_tells_ustaad():
    desk, phone, queue, jobs, _ = session(job=job(step(1), step(2, english="Check the fan")))
    await desk.on_step_done(1)
    (card,) = phone.of(StepCard)
    assert (card.n, card.of, card.instruction) == (2, 2, "Step 2 karo")
    assert jobs.job.current_step == 2
    (notice,) = queue.notices
    assert notice.startswith("[He tapped done on step 1. The app handed out step 2 of 2")
    assert '"Check the fan"' in notice and "in Hindi, written in Devanagari script," in notice
    assert "do not call next_step" in notice


@pytest.mark.parametrize("n", [1, 3, 9])
async def test_a_stale_or_unknown_step_is_ignored(n):
    desk, phone, queue, jobs, _ = session(job=job(step(1), step(2), step(3), handed_out=2))
    await desk.on_step_done(n)
    assert (phone.frames, queue.notices, jobs.job.current_step) == ([], [], 2)


async def test_a_repeated_tap_hands_out_nothing_more():
    desk, phone, queue, jobs, _ = session(job=job(step(1), step(2), step(3)))
    await desk.on_step_done(1)
    await desk.on_step_done(1)
    assert [c.n for c in phone.of(StepCard)] == [2]
    assert (len(queue.notices), jobs.job.current_step) == (1, 2)


async def test_a_gate_before_the_next_step_shows_the_gate_and_its_photo_request_not_the_step():
    desk, phone, queue, jobs, _ = session(job=job(step(1), step(2, hazard="HV")))
    await asyncio.gather(*desk.tasks)
    shown = len(phone.frames)  # tools built on a job with a gate next already show it (a reconnect)
    await desk.on_step_done(1)
    await desk.on_step_done(1)
    after = phone.frames[shown:]
    assert [type(f) for f in after] == [SafetyGate]
    assert [r.target for r in phone.of(MediaRequest)] == [EVIDENCE["G_MAINS_OFF"]]
    assert jobs.job.current_step == 1
    (notice,) = queue.notices
    assert notice.startswith("[He tapped done on step 1. Another safety check comes before the next step: G_MAINS_OFF")
    assert "Step 2 karo" not in notice


async def test_done_on_the_last_step_shows_nothing_and_tells_ustaad_once():
    desk, phone, queue, _, _ = session(job=job(step(1), step(2), handed_out=2))
    await desk.on_step_done(2)
    await desk.on_step_done(2)
    assert phone.frames == []
    assert queue.notices == ["[He tapped done on step 2. Every step has been given.]"]
