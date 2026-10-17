"""A photo of his manual page or wiring sticker (S7, BUILD-GUIDE §9.3, T37): Flash copies the page, code judges it,
and its printed steps become the plan with source kind manual_photo. Vision answers are pages transcribed from the
verified manuals in seed/manual_codes.json; no model is called."""

import asyncio
import json
from pathlib import Path

from agent.media_tools import MediaDesk, media_tools
from agent.repair_tools import repair_tools
from models.repair import RepairJob
from models.tools import ManualPage, StartRepairIn, StepOut
from models.ws import MediaRequest, MediaResult, StepCard
from tests.unit.test_request_media import FakeJobs, FakeQueue, Phone, context, ready
from tools import repair
from tools.request_media import GAVE_UP, MAX_RETAKES, RETAKE, judge_page

PAGES = json.loads((Path(__file__).parents[3] / "seed/fixtures/manual_pages.json").read_text())
URI = "gs://media/jobs/j_1/r_1/page.jpg"


def page(name: str) -> ManualPage:
    return ManualPage.model_validate(PAGES[name])


def test_a_legible_page_gives_its_error_codes():
    out, retake = judge_page(page("voltas_error_table"), URI, 0, "hi", brand="Voltas")
    assert not retake and out.matches_expected
    assert [(f.label, f.value) for f in out.findings][:2] == [("EE", "Indoor machine EE fault"), ("E1", "Indoor fan fault")]


def test_a_blurry_page_is_retaken_with_a_reason_in_hindi_at_most_twice():
    out, retake = judge_page(page("blurry"), URI, 0, "hi", brand=None)
    assert retake and out.follow_up == RETAKE["hi"]["illegible"]
    out, retake = judge_page(page("blurry"), URI, MAX_RETAKES, "hi", brand=None)
    assert not retake and out.follow_up == GAVE_UP


def test_every_language_has_the_illegible_page_reason():
    assert all("illegible" in reasons for reasons in RETAKE.values())


def test_a_page_of_another_brand_is_flagged_not_used():
    out, retake = judge_page(page("daikin_safety_checks"), URI, 0, "hi", brand="Voltas")
    assert not retake and not out.matches_expected
    assert "Daikin" in out.follow_up and "Voltas" in out.follow_up


def test_brand_case_and_spaces_do_not_count_as_another_brand():
    out, _ = judge_page(page("voltas_error_table"), URI, 0, "hi", brand=" VOLTAS ")
    assert out.matches_expected


def test_a_page_describing_gas_work_stops_with_no_steps():
    job = RepairJob(job_id="j_1")
    out, after = repair.start_repair(StartRepairIn(manual_request_id="r_1"), job, [], page("daikin_ch61"))
    assert out.status == "STOP_REFER" and out.reason == "refrigerant"
    assert after.steps == []


def test_page_steps_keep_their_hazards_and_gates_and_cite_the_manual_photo():
    job = RepairJob(job_id="j_1")
    out, job = repair.start_repair(StartRepairIn(manual_request_id="r_1"), job, [], page("daikin_safety_checks"))
    assert [s.hazard for s in job.steps] == ["HV", "capacitor"]
    assert {(s.source.kind, s.source.label) for s in out.steps} == {("manual_photo", "Photo of manual")}
    first, _ = repair.next_step(job)
    assert first.status == "SAFETY_GATE" and first.gate_id == "G_MAINS_OFF"


# Through the session: the phone's offer, the desk, and start_repair as the Live agent calls it.


class PageJobs(FakeJobs):
    def fault_cards(self, ids):
        return []


def session(*pages: str, brand: str | None = None):
    desk, phone, queue, jobs = MediaDesk("j_1", "media"), Phone(), FakeQueue(), PageJobs()
    desk.attach(phone.send, queue, "hi")
    desk.brand = brand
    answers = iter(page(name) for name in pages)

    async def vision(question, uri, schema):
        assert schema is ManualPage
        return next(answers)

    media_tools(desk, jobs, vision)
    return desk, phone, queue, jobs


async def send_page(desk, phone):
    request = phone.of(MediaRequest)[-1]
    assert desk.ready(ready(request.request_id, kind="document"))
    await asyncio.gather(*desk.tasks)
    return request.request_id


async def test_his_manual_page_is_read_and_ustaad_hears_the_codes_and_how_to_use_it():
    desk, phone, queue, jobs = session("voltas_error_table", brand="Voltas")
    await desk.offer("document")
    request_id = await send_page(desk, phone)
    (notice,) = queue.notices
    assert "Indoor fan fault" in notice and request_id in notice
    assert desk.pages[request_id].brand == "VOLTAS"
    (entry,) = jobs.job.media
    assert (entry.kind, entry.reason) == ("document", "manual")
    assert ("E1", "Indoor fan fault") in [(f.label, f.value) for f in entry.findings]


async def test_ustaad_never_hears_a_page_step_before_next_step_gives_it():
    desk, phone, queue, _ = session("daikin_safety_checks")
    await desk.offer("document")
    await send_page(desk, phone)
    (notice,) = queue.notices
    assert "capacitor" not in notice.lower()


async def test_a_blurry_page_shows_the_retake_reason_and_is_not_kept():
    desk, phone, queue, _ = session("blurry")
    await desk.offer("document")
    await send_page(desk, phone)
    (result,) = phone.of(MediaResult)
    assert result.retake_reason == RETAKE["hi"]["illegible"]
    assert desk.pages == {} and queue.notices == []


async def test_another_brands_page_is_not_kept():
    desk, phone, queue, _ = session("daikin_safety_checks", brand="Voltas")
    await desk.offer("document")
    await send_page(desk, phone)
    assert desk.pages == {}
    (notice,) = queue.notices
    assert "Daikin" in notice


async def test_start_repair_from_his_page_shows_step_cards_citing_the_photo_of_manual():
    desk, phone, _, jobs = session("daikin_safety_checks")
    await desk.offer("document")
    request_id = await send_page(desk, phone)
    start_repair, next_step = repair_tools(jobs, desk)
    out = start_repair.func(context(), manual_request_id=request_id)
    assert out["status"] == "STARTED" and out["of"] == 2
    jobs.job = jobs.job.model_copy(update={"gates": {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "open"}})
    step = next_step.func(context(), observation="")
    card = repair.step_card(StepOut.model_validate(step), "hi")
    assert isinstance(card, StepCard)
    assert (card.source.kind, card.source.label) == ("manual_photo", "Photo of manual")


async def test_start_repair_with_an_unknown_page_tells_ustaad_to_ask_for_it():
    desk, _, _, jobs = session()
    out = repair_tools(jobs, desk)[0].func(context(), manual_request_id="r_nothere")
    assert out["status"] == "NO_PAGE"
    assert jobs.job.steps == []
