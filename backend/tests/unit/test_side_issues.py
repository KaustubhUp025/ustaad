"""Side issues mid-repair (S7, BUILD-GUIDE §9.2, §9.7 A): he raises a second problem at a step; the main repair is
parked and resumed at the same step, through next_step's gates; a side finding is logged and kept; close_job can
draft a second card for it. Placeholder text only, no real repair steps. No model is called."""

from datetime import UTC, datetime
from types import SimpleNamespace

from agent.close_tools import close_tools
from agent.media_tools import MediaDesk, media_tools
from agent.repair_tools import repair_tools
from models.repair import JobMedia, Observation, RepairJob, RepairStep
from models.tools import (
    CloseJobIn,
    MediaCheck,
    NothingToPark,
    Parked,
    ParkedPlan,
    ProposedStep,
    RepairDone,
    SafetyGateOut,
    SideFix,
    StartRepairIn,
    StepOut,
    StopRefer,
)
from models.ws import MediaRequest, StepCard
from tests.unit.fake_cards import FakeCardStore, embed
from tests.unit.fake_inventory import FakeInventoryStore, stock
from tests.unit.test_request_media import FakeJobs, FakeQueue, Phone, photo
from tools import repair
from tools.close_job import close_job, side_card

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
NOTE = {"kind": "whatsapp_voice", "label": "Test senior", "audio_uri": None, "doc": None, "page": None}
OPEN = {"G_MAINS_OFF": "open", "G_CAP_DISCHARGE": "open"}
PASSED = {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "passed"}
WIRE = JobMedia(
    request_id="r_wire",
    uri="gs://media/jobs/j_1/r_wire/w.jpg",
    kind="photo",
    findings=[Observation(label="wire", value="insulation burnt", confidence=0.9)],
    confidence=0.9,
    reason="side_issue",
)


def step(n: int, hazard="none") -> RepairStep:
    return RepairStep(n=n, instruction=f"Test main step {n}", hazard=hazard, source=NOTE)


def at_step_3(hazard="none", gates=OPEN) -> RepairJob:
    """The main repair: step 3 of 6 handed out."""
    steps = [step(n, hazard if n == 3 else "none") for n in range(1, 7)]
    return RepairJob(job_id="j_1", steps=steps, current_step=3, gates=gates)


def side_plan(job: RepairJob, summary="Test side check of the burnt wire at the PCB") -> RepairJob:
    """'abhi': a plan of its own for the side issue, started with start_repair as any plan is."""
    proposed = ProposedStep(instruction="Test side step", summary_en=summary)
    out, after = repair.start_repair(StartRepairIn(steps=[proposed]), job, [])
    assert out.status == "STARTED"
    return after


# The pure rules.


def test_park_holds_the_step_he_is_on():
    out, plan = repair.park(at_step_3(), "burnt wire")
    assert out == Parked(n=3, of=6)
    assert (plan.current_step, len(plan.steps), plan.issue) == (3, 6, "burnt wire")


def test_nothing_to_park_before_the_first_step():
    assert repair.park(RepairJob(job_id="j_1", steps=[step(1)]), "burnt wire") == (NothingToPark(), None)


def test_baad_mein_resumes_the_same_step_and_keeps_its_gates():
    job = at_step_3(hazard="HV", gates=PASSED)
    out, after = repair.resume(job, None)
    assert isinstance(out, StepOut) and out.step.n == 3
    assert (after.current_step, after.gates) == (3, PASSED)


def test_abhi_then_resume_brings_back_the_main_step():
    job = at_step_3()
    _, plan = repair.park(job, "burnt wire")
    out, after = repair.resume(side_plan(job), plan)
    assert isinstance(out, StepOut) and (out.step.n, out.step.instruction, out.of) == (3, "Test main step 3", 6)
    assert after.current_step == 3


def test_a_parked_hv_step_needs_its_gate_again_after_the_side_plan():
    # SAFETY.md: a passed gate holds only for its plan; the side work was a plan of its own and power may be back on.
    job = at_step_3(hazard="HV", gates=PASSED)
    _, plan = repair.park(job, "burnt wire")
    out, after = repair.resume(side_plan(job), plan)
    assert out == SafetyGateOut(gate_id="G_MAINS_OFF", required_evidence=out.required_evidence)
    assert after.current_step == 2


def test_an_hv_side_issue_needs_mains_off_before_its_first_step():
    out, _ = repair.next_step(side_plan(at_step_3(gates=PASSED)))
    assert isinstance(out, SafetyGateOut) and out.gate_id == "G_MAINS_OFF"


def test_a_gas_side_issue_stops_and_leaves_the_main_repair_as_it_was():
    job = at_step_3()
    gas = ProposedStep(instruction="Test side step", summary_en="Test check of the gas leak")
    out, after = repair.start_repair(StartRepairIn(steps=[gas]), job, [])
    assert out == StopRefer(reason="refrigerant")
    assert after == job


def test_a_new_plan_keeps_the_logged_side_finding_and_opens_every_gate():
    after = side_plan(at_step_3(gates=PASSED).model_copy(update={"media": [WIRE]}))
    assert (after.media, after.gates, after.current_step) == ([WIRE], OPEN, 0)


def test_resume_with_nothing_handed_out_gives_the_first_step_and_after_the_last_gives_the_last():
    fresh = RepairJob(job_id="j_1", steps=[step(1), step(2)])
    assert repair.resume(fresh, None)[0].step.n == 1
    done = fresh.model_copy(update={"current_step": 2})
    assert repair.resume(done, None)[0].step.n == 2
    assert isinstance(repair.resume(RepairJob(job_id="j_1"), None)[0], RepairDone)


def test_a_fixed_side_issue_drafts_a_second_card_with_its_photo():
    main_photo = WIRE.model_copy(update={"request_id": "r_pcb", "uri": "gs://media/jobs/j_1/r_pcb/p.jpg", "reason": "requested"})
    job = at_step_3(gates=PASSED).model_copy(update={"current_step": 6, "media": [main_photo, WIRE]})
    inp = CloseJobIn(
        symptom="Test main symptom",
        outcome="Test main cause",
        fix_summary="Test main fix",
        error_code="E6",
        side_fix=SideFix(symptom="Test burnt wire", outcome="Test wire cause", fix_summary="Test wire fix"),
    )
    _, _, main = close_job(inp, job, "fc_main", NOW)
    side = side_card(inp, job, "fc_side", NOW)
    assert main.photo_uri == "gs://media/jobs/j_1/r_pcb/p.jpg"
    assert (side.id, side.symptom, side.photo_uri) == ("fc_side", "Test burnt wire (found while fixing E6)", WIRE.uri)
    assert (side.root_cause, side.fix_steps, side.review_status) == ("Test wire cause", ["Test wire fix"], "needs_review")
    assert side_card(inp.model_copy(update={"side_fix": None}), job, "fc_side", NOW) is None


def test_the_main_card_never_takes_the_side_photo():
    job = at_step_3(gates=PASSED).model_copy(update={"current_step": 6, "media": [WIRE]})
    _, _, card = close_job(CloseJobIn(symptom="s", outcome="o", fix_summary="f"), job, "fc_main", NOW)
    assert card.photo_uri is None


# The tools as the Live agent calls them.


def tools(job: RepairJob):
    desk, phone, queue, jobs = MediaDesk("j_1", "media"), Phone(), FakeQueue(), FakeJobs(job)
    desk.attach(phone.send, queue, "hi")
    named = {t.name: t for t in repair_tools(jobs, desk)}
    return named, jobs, SimpleNamespace(state={"job_id": "j_1", "lang": "hi", "worker_id": "w_hi_demo"})


def test_park_and_resume_are_blocking():
    named, _, _ = tools(at_step_3())
    assert {n: t.behavior.name for n, t in named.items() if n in ("park_repair", "resume_repair")} == {
        "park_repair": "BLOCKING",
        "resume_repair": "BLOCKING",
    }


def test_abhi_parks_then_resume_repair_hands_out_the_same_step_card():
    named, jobs, ctx = tools(at_step_3())
    assert named["park_repair"].func(ctx, issue="burnt wire") == {"status": "PARKED", "n": 3, "of": 6}
    jobs.job = side_plan(jobs.job)
    out = named["resume_repair"].func(ctx)
    assert (out["status"], out["step"]["n"], out["step"]["instruction"]) == ("STEP", 3, "Test main step 3")
    assert ctx.state["parked"] is None


def test_a_third_issue_is_noted_not_nested():
    named, _, ctx = tools(at_step_3())
    named["park_repair"].func(ctx, issue="burnt wire")
    out = named["park_repair"].func(ctx, issue="loose screw")
    assert out == {"status": "ALREADY_PARKED", "noted": "loose screw"}
    assert ParkedPlan.model_validate(ctx.state["parked"]).issue == "burnt wire"
    assert ctx.state["side_issues"] == ["loose screw"]


async def test_ustaads_side_issue_photo_is_logged_as_a_side_issue():
    desk, phone, queue, jobs = MediaDesk("j_1", "media"), Phone(), FakeQueue(), FakeJobs(at_step_3())
    desk.attach(phone.send, queue, "hi")
    clear = MediaCheck(matches_expected=True, confidence=0.9, problem=None, findings=[{"label": "wire", "value": "burnt", "confidence": 0.8}])

    async def vision(question, uri, schema):
        return clear

    tool = media_tools(desk, jobs, vision)[0]
    ctx = SimpleNamespace(state={"job_id": "j_1", "lang": "hi"}, function_call_id="call_1")
    await tool.func(ctx, kind="photo", target="Jala hua wire", reason="side_issue", framing_tip="paas se")
    await photo(desk, phone.of(MediaRequest)[0].request_id)
    assert [m.reason for m in jobs.job.media] == ["side_issue"]


async def test_close_job_saves_the_side_card_too():
    job = at_step_3(gates=PASSED).model_copy(update={"current_step": 6, "media": [WIRE]})
    desk, cards = MediaDesk("j_1", "media"), FakeCardStore()
    desk.attach(Phone().send, FakeQueue(), "hi")
    tool = close_tools(FakeJobs(job), cards, FakeInventoryStore(stock()), desk, embed)[0]
    side = {"symptom": "Test burnt wire", "outcome": "Test wire cause", "fix_summary": "Test wire fix"}
    out = await tool.func(
        SimpleNamespace(state={"job_id": "j_1", "worker_id": "w_hi_demo"}),
        symptom="s",
        outcome="o",
        fix_summary="f",
        side_fix=side,
    )
    assert out["status"] == "CLOSED" and out["side_card_id"] in cards.cards
    assert {c.symptom for c, _ in cards.cards.values()} == {"s", "Test burnt wire (found while fixing s)"}


def test_the_resumed_step_reaches_the_phone_as_a_step_card():
    from app.live_events import _tool_frame

    named, _, ctx = tools(at_step_3())
    frame = _tool_frame("resume_repair", named["resume_repair"].func(ctx), "hi")
    assert isinstance(frame, StepCard) and frame.n == 3
