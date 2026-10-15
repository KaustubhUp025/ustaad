"""request_media (M4, BUILD-GUIDE T17): the retake rules, the job's open requests, and the tool as the Live agent
calls it. No model is called: vision answers are recorded checks, the job store and the Live queue are fakes."""

import asyncio
from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk, media_tools
from models.repair import RepairJob, RepairStep
from models.tools import GateCheck, MediaCheck, RequestMediaIn
from models.ws import GateResult, MediaCancel, MediaReady, MediaRequest, MediaResult
from tools.gates import EVIDENCE
from tools.request_media import CANCELLED, GATE_RETAKE, MAX_RETAKES, NOT_CHECKED, RETAKE, judge, record

URI = "gs://media/jobs/j_1/a1-photo.jpg"
PCB = RequestMediaIn(kind="photo", target="Outdoor PCB, capacitor ke paas", reason="code E6", framing_tip="Flash on")
BLURRY = MediaCheck(matches_expected=True, confidence=0.41, problem="blurry", findings=[])
WALL = MediaCheck(matches_expected=False, confidence=0.95, problem="not_visible", findings=[])
CLEAR = MediaCheck(
    matches_expected=True,
    confidence=0.9,
    problem=None,
    findings=[{"label": "capacitor", "value": "bulged top", "confidence": 0.8}],
)
MCB_OFF = GateCheck(passed=True, reason=None, confidence=0.9)
NO_MCB = GateCheck(passed=False, reason="Only a wall in the photo", confidence=0.95)


def test_poor_photo_asks_for_a_retake_with_a_reason_in_his_language():
    out, retake = judge(BLURRY, URI, 0, "hi")
    assert retake and out.retaking
    assert out.follow_up == RETAKE["hi"]["blurry"]
    assert not out.matches_expected


def test_a_confident_photo_of_something_else_is_also_retaken():
    out, retake = judge(WALL, URI, 0, "te")
    assert retake
    assert out.follow_up == RETAKE["te"]["not_visible"]


def test_after_the_last_retake_it_stops_asking_and_continues_with_a_note():
    out, retake = judge(BLURRY, URI, MAX_RETAKES, "hi")
    assert not retake and not out.retaking
    assert out.follow_up and out.follow_up not in RETAKE["hi"].values()
    assert out.media_uri == URI


def test_a_clear_matching_photo_is_accepted():
    out, retake = judge(CLEAR, URI, 0, "hi")
    assert not retake
    assert out.matches_expected and out.follow_up is None
    assert [f.label for f in out.findings] == ["capacitor"]


def test_every_language_has_every_retake_reason():
    assert set(RETAKE) == {"hi", "te", "ta", "bn", "en"}
    assert all(set(reasons) == set(RETAKE["en"]) for reasons in RETAKE.values())
    assert set(GATE_RETAKE) == set(RETAKE)
    assert all(set(reasons) == {"G_MAINS_OFF", "G_CAP_DISCHARGE"} for reasons in GATE_RETAKE.values())


def test_record_lists_the_photo_on_the_job():
    job = record(RepairJob(job_id="j_1"), "r_1", "photo", URI, CLEAR.findings, CLEAR.confidence)
    assert [(m.request_id, m.uri, m.kind, m.reason) for m in job.media] == [("r_1", URI, "photo", "requested")]


# Fakes for the session around the desk


class FakeJobs:
    def __init__(self, job=None):
        self.job = job or RepairJob(job_id="j_1")

    def load(self, job_id):
        return self.job

    def update(self, job_id, change):
        out, self.job = change(self.job)
        return out


class FakeQueue:
    """Collects what the desk sends the model: answers to its calls, and notices for requests it did not make."""

    def __init__(self):
        self.answers = []
        self.notices = []

    def send_content(self, content):
        part = content.parts[0]
        if part.function_response:
            self.answers.append(part.function_response)
        else:
            self.notices.append(part.text)


class Phone:
    def __init__(self):
        self.frames = []

    async def send(self, frame):
        self.frames.append(frame)

    def of(self, kind):
        return [f for f in self.frames if isinstance(f, kind)]


def session(checks=(), gate_checks=(), job=None):
    """A desk attached to one phone connection, with the tool built around recorded vision answers (an exception in
    the list is raised, as a failed vision call would)."""
    desk, phone, queue, jobs = MediaDesk("j_1", "media"), Phone(), FakeQueue(), FakeJobs(job)
    desk.attach(phone.send, queue, "hi")
    answers = {MediaCheck: iter(checks), GateCheck: iter(gate_checks)}

    async def vision(question, uri, schema):
        answer = next(answers[schema])
        if isinstance(answer, Exception):
            raise answer
        return answer

    tool = media_tools(desk, jobs, vision)[0]
    return desk, phone, queue, jobs, tool


def context(call_id="call_1"):
    return SimpleNamespace(state={"job_id": "j_1", "lang": "hi"}, function_call_id=call_id)


def ready(request_id, uri=URI, kind="photo"):
    return MediaReady(request_id=request_id, uri=uri, kind=kind)


async def photo(desk, request_id, uri=URI):
    assert desk.ready(ready(request_id, uri))
    await asyncio.gather(*desk.tasks)


def test_request_media_is_non_blocking_long_running_and_answers_when_idle():
    tool = session()[4]
    assert tool.behavior == types.Behavior.NON_BLOCKING
    assert tool.is_long_running
    assert tool.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


async def test_the_tool_sends_media_request_and_leaves_the_answer_to_the_desk():
    _, phone, queue, _, tool = session()
    assert await tool.func(context(), **PCB.model_dump()) is None
    (request,) = phone.of(MediaRequest)
    assert (request.target, request.framing_tip, request.max_seconds) == (PCB.target, "Flash on", None)
    assert queue.answers == []


async def test_media_ready_for_an_unknown_finished_foreign_or_wrong_kind_request_is_rejected():
    desk, phone, _, _, tool = session(checks=[CLEAR])
    assert not desk.ready(ready("r_x"))
    await tool.func(context(), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    assert not desk.ready(ready(rid, uri="gs://media/jobs/j_2/a1-photo.jpg"))
    assert not desk.ready(ready(rid, uri="gs://other/jobs/j_1/a1-photo.jpg"))
    assert not desk.ready(ready(rid, kind="video"))
    await photo(desk, rid)
    assert not desk.ready(ready(rid))


async def test_blurry_then_clear_answers_the_same_call_twice_and_records_only_the_good_photo():
    desk, phone, queue, jobs, tool = session(checks=[BLURRY, CLEAR])
    await tool.func(context("call_7"), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    await photo(desk, rid, "gs://media/jobs/j_1/a1-blurry.jpg")
    await photo(desk, rid)

    assert [(r.request_id, r.retake_reason) for r in phone.of(MediaResult)] == [
        (rid, RETAKE["hi"]["blurry"]),
        (rid, None),
    ]
    # One spoken answer per photo, on the model's one call, delivered when Ustaad is idle.
    assert [(a.id, a.name, a.scheduling) for a in queue.answers] == [
        ("call_7", "request_media", types.FunctionResponseScheduling.WHEN_IDLE)
    ] * 2
    assert queue.answers[0].response["retaking"] and queue.answers[0].response["follow_up"] == RETAKE["hi"]["blurry"]
    assert queue.answers[1].response["matches_expected"] and not queue.answers[1].response["retaking"]
    assert [m.uri for m in jobs.job.media] == [URI]


async def test_cancel_answers_the_call_and_closes_the_request():
    desk, phone, queue, _, tool = session()
    await tool.func(context(), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    assert desk.cancel(MediaCancel(request_id=rid))
    assert queue.answers[0].response["follow_up"] == CANCELLED
    assert not desk.ready(ready(rid))


# A dropped connection: the request belongs to the job, not to the socket


async def test_after_a_reconnect_the_phone_gets_the_open_request_again_and_the_answer_reaches_the_new_session():
    desk, phone, old_queue, jobs, tool = session()
    await tool.func(context("call_9"), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    desk.detach()

    # The reconnect builds a new agent, so new tools, around the same job's desk.
    async def vision(question, uri, schema):
        return CLEAR

    media_tools(desk, jobs, vision)
    new_phone, new_queue = Phone(), FakeQueue()
    desk.attach(new_phone.send, new_queue, "hi")
    await asyncio.gather(*desk.tasks)
    assert [f.request_id for f in new_phone.of(MediaRequest)] == [rid]
    await photo(desk, rid)
    assert old_queue.answers == []
    assert [a.id for a in new_queue.answers] == ["call_9"]


async def test_an_answer_ready_while_disconnected_is_held_until_the_next_connection():
    desk, phone, _, _, tool = session(checks=[CLEAR])
    await tool.func(context("call_3"), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    assert desk.ready(ready(rid))
    desk.detach()
    await asyncio.gather(*desk.tasks)

    new_queue = FakeQueue()
    desk.attach(Phone().send, new_queue, "hi")
    await asyncio.gather(*desk.tasks)
    assert [a.id for a in new_queue.answers] == ["call_3"]


# Gate photos: one vision call, judged by the gate rules, no retake limit (docs/SAFETY.md)


async def test_a_gate_photo_is_judged_by_the_gate_check_alone_and_retakes_until_it_passes():
    fails = [NO_MCB] * (MAX_RETAKES + 2)
    desk, phone, queue, jobs, tool = session(gate_checks=[*fails, MCB_OFF])
    gate_photo = RequestMediaIn(kind="photo", target="MCB OFF", reason="gate", framing_tip="", gate_id="G_MAINS_OFF")
    await tool.func(context("call_g"), **gate_photo.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    for _ in fails:
        await photo(desk, rid)
    assert jobs.job.gates["G_MAINS_OFF"] == "failed"
    await photo(desk, rid)

    assert [g.passed for g in phone.of(GateResult)] == [False] * len(fails) + [True]
    # The sheet shows a fixed reason in his language; the model gets the gate check's own reason.
    assert {r.retake_reason for r in phone.of(MediaResult)[:-1]} == {GATE_RETAKE["hi"]["G_MAINS_OFF"]}
    assert queue.answers[0].response["reason"] == NO_MCB.reason
    assert phone.of(MediaResult)[-1].retake_reason is None
    assert jobs.job.gates["G_MAINS_OFF"] == "passed"
    assert [a.response["passed"] for a in queue.answers] == [False] * len(fails) + [True]
    assert not desk.ready(ready(rid))


# The server opens a gate's photo request itself: measured on Oct 15, Ustaad opened one for only 1 of 5 gates.

GENERAL = {"kind": "general", "label": "General guidance", "audio_uri": None, "doc": None, "page": None}


def gated_job():
    """A job whose next step is an HV step, so G_MAINS_OFF stands before it."""
    step = RepairStep(n=1, instruction="Test step at the PCB", hazard="HV", source=GENERAL)
    return RepairJob(job_id="j_1", steps=[step])


async def test_a_safety_gate_opens_its_photo_request_once_without_the_model():
    desk, phone, queue, _, _ = session()
    await desk.open_gate("G_MAINS_OFF")
    await desk.open_gate("G_MAINS_OFF")
    (request,) = phone.of(MediaRequest)
    assert (request.kind, request.target, request.framing_tip) == ("photo", EVIDENCE["G_MAINS_OFF"], "")
    assert queue.answers == [] and queue.notices == []


async def test_a_server_opened_gate_photo_is_judged_and_ustaad_gets_a_notice():
    desk, phone, queue, jobs, _ = session(gate_checks=[NO_MCB, MCB_OFF], job=gated_job())
    await desk.open_gate("G_MAINS_OFF")
    rid = phone.of(MediaRequest)[0].request_id
    await photo(desk, rid)
    await photo(desk, rid)
    assert [g.passed for g in phone.of(GateResult)] == [False, True]
    assert phone.of(MediaResult)[0].retake_reason == GATE_RETAKE["hi"]["G_MAINS_OFF"]
    assert jobs.job.gates["G_MAINS_OFF"] == "passed"
    assert queue.answers == []
    assert len(queue.notices) == 2 and "G_MAINS_OFF" in queue.notices[1] and "next_step" in queue.notices[1]
    assert not desk.ready(ready(rid))


async def test_ustaads_own_gate_request_joins_the_open_one_and_gets_the_answer():
    desk, phone, queue, _, tool = session(gate_checks=[MCB_OFF], job=gated_job())
    await desk.open_gate("G_MAINS_OFF")
    gate_photo = RequestMediaIn(kind="photo", target="MCB OFF", reason="gate", framing_tip="", gate_id="G_MAINS_OFF")
    await tool.func(context("call_g"), **gate_photo.model_dump())
    (request,) = phone.of(MediaRequest)
    await photo(desk, request.request_id)
    assert [(a.id, a.response["passed"]) for a in queue.answers] == [("call_g", True)]
    assert queue.notices == []


async def test_a_reconnect_reopens_the_gate_request_from_the_job_alone():
    desk = MediaDesk("j_1", "media")
    phone = Phone()
    desk.attach(phone.send, FakeQueue(), "hi")
    media_tools(desk, FakeJobs(gated_job()), None)
    await asyncio.gather(*desk.tasks)
    assert [r.target for r in phone.of(MediaRequest)] == [EVIDENCE["G_MAINS_OFF"]]


# A vision call that fails or hangs must not leave the sheet waiting forever.


async def test_a_failed_vision_check_asks_him_to_send_again_and_keeps_the_request():
    desk, phone, queue, _, tool = session(checks=[RuntimeError("429 quota"), CLEAR])
    await tool.func(context(), **PCB.model_dump())
    rid = phone.of(MediaRequest)[0].request_id
    await photo(desk, rid)
    assert phone.of(MediaResult)[-1].retake_reason == NOT_CHECKED["hi"]
    assert queue.answers == []
    await photo(desk, rid)
    assert queue.answers[-1].response["matches_expected"]


async def test_a_hung_vision_check_times_out(monkeypatch):
    from agent import media_tools as module

    monkeypatch.setattr(module, "VISION_TIMEOUT_S", 0.01)
    desk, phone, _, _, _ = session()

    async def hangs(question, uri, schema):
        await asyncio.sleep(1)

    tool = media_tools(desk, FakeJobs(), hangs)[0]
    await tool.func(context(), **PCB.model_dump())
    await photo(desk, phone.of(MediaRequest)[0].request_id)
    assert phone.of(MediaResult)[-1].retake_reason == NOT_CHECKED["hi"]


def test_every_language_has_the_not_checked_reason():
    assert set(NOT_CHECKED) == set(RETAKE)


# The worker starts a photo himself (media_offer): measured on Oct 15, Ustaad opened a request for only 1 of 3 offers.


async def test_his_own_photo_opens_a_server_request_and_ustaad_gets_the_findings():
    desk, phone, queue, jobs, _ = session(checks=[CLEAR])
    await desk.offer("photo")
    (request,) = phone.of(MediaRequest)
    assert (request.kind, request.target) == ("photo", "")
    await photo(desk, request.request_id)
    assert queue.answers == []
    (notice,) = queue.notices
    assert notice.startswith("[Photo from the worker") and "bulged top" in notice
    assert [(m.uri, m.reason) for m in jobs.job.media] == [(URI, "side_issue")]


async def test_his_manual_page_is_recorded_as_manual():
    desk, phone, _, jobs, _ = session(checks=[CLEAR])
    await desk.offer("document")
    request = phone.of(MediaRequest)[0]
    assert request.kind == "document"
    assert desk.ready(ready(request.request_id, kind="document"))
    await asyncio.gather(*desk.tasks)
    assert [m.reason for m in jobs.job.media] == ["manual"]


async def test_his_offer_during_a_gate_goes_to_the_gate_request():
    desk, phone, _, _, _ = session(job=gated_job())
    await desk.open_gate("G_MAINS_OFF")
    await desk.offer("photo")
    gate_request, again = phone.of(MediaRequest)
    assert again == gate_request


async def test_his_offer_while_ustaad_waits_for_a_photo_answers_ustaads_request():
    desk, phone, _, _, tool = session()
    await tool.func(context(), **PCB.model_dump())
    await desk.offer("photo")
    asked, again = phone.of(MediaRequest)
    assert again == asked


async def test_a_poor_photo_of_his_own_is_retaken_without_bothering_ustaad():
    desk, phone, queue, _, _ = session(checks=[BLURRY, CLEAR])
    await desk.offer("photo")
    rid = phone.of(MediaRequest)[0].request_id
    await photo(desk, rid)
    assert phone.of(MediaResult)[-1].retake_reason == RETAKE["hi"]["blurry"]
    assert queue.notices == []
    await photo(desk, rid)
    assert len(queue.notices) == 1


def test_his_own_photo_is_retaken_only_when_blurry_or_dark():
    out, retake = judge(WALL, URI, 0, "hi", own=True)
    assert not retake and out.matches_expected and out.follow_up is None
    _, retake = judge(BLURRY, URI, 0, "hi", own=True)
    assert retake
