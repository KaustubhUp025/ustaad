"""Step-card translation for te/ta/bn (CHANGELOG 2026-10-17): one background Flash call after start_repair, stored
on the job with its language, shown only in a session of that language; display-only, the original on any failure."""

import asyncio
import logging
from types import SimpleNamespace

import pytest

from agent.media_tools import MediaDesk
from agent.repair_tools import repair_tools
from models.repair import RepairJob, RepairStep, StepSource
from models.tools import StepTranslations
from tools.repair import GENERAL, next_step, step_card
from tools.translate_steps import apply, prompt, sources

CARD = StepSource(kind="whatsapp_voice", label="Ramesh · May 2025", audio_uri="gs://b/n.flac", doc=None, page=None)
TELUGU = ["పరీక్ష ఒకటి", "పరీక్ష రెండు"]  # "test one", "test two"


def job(**changes) -> RepairJob:
    steps = [
        RepairStep(n=1, instruction="Test ek", instruction_en="Test one", hazard="HV", source=CARD),
        RepairStep(n=2, instruction="Test do", instruction_en=None, hazard="capacitor", source=GENERAL),
    ]
    passed = {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "passed"}
    return RepairJob(job_id="j_1", steps=steps, **({"gates": passed} | changes))


def test_the_prompt_numbers_every_line_and_asks_for_the_same_count():
    text = prompt(sources(job()), "Telugu, written in Telugu script")
    assert "1. Test one" in text and "2. Test do" in text  # the original when a step has no English
    assert "exactly 2 lines" in text and "Telugu, written in Telugu script" in text


def test_a_full_translation_is_stored_with_its_language():
    done = apply(job(), "te", sources(job()), TELUGU)
    assert [s.instruction_translated for s in done.steps] == TELUGU
    assert done.translation_lang == "te"


@pytest.mark.parametrize("lines", [TELUGU[:1], [*TELUGU, "పరీక్ష మూడు"], [TELUGU[0], "  "], []])
def test_a_wrong_count_or_a_blank_line_stores_nothing(lines):
    assert apply(job(), "te", sources(job()), lines) == job()


def test_a_translation_of_an_older_plan_is_not_stored():
    asked = sources(job())
    replanned = job().model_copy(update={"steps": [job().steps[1].model_copy(update={"n": 1})]})
    assert apply(replanned, "te", asked, TELUGU[:1]) == replanned


def test_the_translation_never_changes_hazard_order_gates_or_sources():
    before = job(current_step=1)
    after = apply(before, "te", sources(before), TELUGU)
    strip = {"steps": {"__all__": {"instruction_translated"}}, "translation_lang": True}
    assert after.model_dump(exclude=strip) == before.model_dump(exclude=strip)
    assert next_step(after)[0].step.model_dump(exclude={"instruction_translated"}) == next_step(before)[0].step.model_dump(
        exclude={"instruction_translated"}
    )


@pytest.mark.parametrize(
    ("lang", "shown"), [("te", TELUGU[0]), ("ta", None), ("bn", None), ("hi", None), ("en", "Test one")]
)
def test_the_card_shows_a_translation_only_in_a_session_of_its_language(lang, shown):
    translated = apply(job(), "te", sources(job()), TELUGU)
    card = step_card(next_step(translated)[0], lang)
    assert (card.instruction, card.instruction_translated) == ("Test ek", shown)


# The agent wrapper: the call runs after start_repair returns, and failures are fixed and safe.


class FakeJobs:
    def __init__(self):
        self.job = RepairJob(job_id="j_1")

    def load(self, job_id):
        return self.job

    def update(self, job_id, change):
        out, self.job = change(self.job)
        return out

    def fault_cards(self, card_ids):
        return []


def started(ask, lang="te"):
    jobs, desk = FakeJobs(), MediaDesk("j_1", "media")
    start = repair_tools(jobs, desk, ask)[0]
    state = {"job_id": "j_1", "lang": lang, "language_name": "Telugu, written in Telugu script"}
    steps = [{"instruction": "Test ek", "summary_en": "Test one"}, {"instruction": "Test do", "summary_en": "Test two"}]
    out = start.func(SimpleNamespace(state=state), steps=steps)
    return out, jobs, desk


async def test_a_telugu_session_gets_the_steps_translated_in_the_background_and_a_reload_keeps_them():
    asked = []

    async def ask(text, schema):
        asked.append(text)
        return StepTranslations(lines=TELUGU)

    out, jobs, desk = started(ask)
    assert out["status"] == "STARTED" and jobs.job.translation_lang is None  # the start did not wait
    await asyncio.gather(*desk.tasks)
    assert len(asked) == 1 and jobs.job.translation_lang == "te"
    reloaded = jobs.load("j_1").model_copy(update={"gates": {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "passed"}})
    assert step_card(next_step(reloaded)[0], "te").instruction_translated == TELUGU[0]


@pytest.mark.parametrize("lang", ["hi", "en"])
async def test_hindi_and_english_sessions_make_no_translation_call(lang):
    async def ask(text, schema):
        raise AssertionError("no call expected")

    _, jobs, desk = started(ask, lang)
    await asyncio.gather(*desk.tasks)
    assert jobs.job.translation_lang is None


async def test_a_failed_call_keeps_the_original_and_logs_only_a_fixed_line(caplog):
    async def ask(text, schema):
        raise RuntimeError("Test secret prompt text")

    _, jobs, desk = started(ask)
    with caplog.at_level(logging.WARNING):
        await asyncio.gather(*desk.tasks)
    assert jobs.job.translation_lang is None and all(s.instruction_translated is None for s in jobs.job.steps)
    assert "Test secret" not in caplog.text and "RuntimeError" in caplog.text
