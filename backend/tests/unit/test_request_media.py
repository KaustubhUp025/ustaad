"""request_media (M4, BUILD-GUIDE T17): the retake rules, the job's open requests, and the tool as the Live agent
calls it. No model is called: vision answers are recorded checks, the job store and the Live queue are fakes."""

import asyncio
from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk, media_tools
from models.repair import RepairJob
from models.tools import GateCheck, MediaCheck, RequestMediaIn
from models.ws import GateResult, MediaCancel, MediaReady, MediaRequest, MediaResult
from tools.request_media import CANCELLED, GATE_RETAKE, MAX_RETAKES, RETAKE, judge, record

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
    def __init__(self):
        self.job = RepairJob(job_id="j_1")

    def load(self, job_id):
        return self.job

    def update(self, job_id, change):
        out, self.job = change(self.job)
        return out


class FakeQueue:
    """Collects what the desk sends the model: function responses as Content."""

    def __init__(self):
        self.answers = []

    def send_content(self, content):
        self.answers.append(content.parts[0].function_response)


class Phone:
    def __init__(self):
        self.frames = []

    async def send(self, frame):
        self.frames.append(frame)

    def of(self, kind):
        return [f for f in self.frames if isinstance(f, kind)]


def session(checks=(), gate_checks=()):
    """A desk attached to one phone connection, with the tool built around recorded vision answers."""
    desk, phone, queue, jobs = MediaDesk("j_1", "media"), Phone(), FakeQueue(), FakeJobs()
    desk.attach(phone.send, queue)
    answers = {MediaCheck: iter(checks), GateCheck: iter(gate_checks)}

    async def vision(question, uri, schema):
        return next(answers[schema])

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
    desk.attach(new_phone.send, new_queue)
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
    desk.attach(Phone().send, new_queue)
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
