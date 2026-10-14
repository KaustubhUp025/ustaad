"""request_media (M4, BUILD-GUIDE T17): the retake rules, the session's open requests, and the tool as the Live
agent calls it. No model is called: the vision check is a recorded MediaCheck and the job store is a fake."""

import asyncio
from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk, media_tools
from agent.repair_tools import repair_tools
from models.repair import RepairJob
from models.tools import GateCheck, MediaCheck, RequestMediaIn
from models.ws import MediaReady, MediaRequest, MediaResult
from tools.request_media import MAX_RETAKES, RETAKE, judge, record

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


def test_poor_photo_asks_for_a_retake_with_a_reason_in_his_language():
    out, retake = judge(BLURRY, URI, 0, "hi")
    assert retake
    assert out.follow_up == RETAKE["hi"]["blurry"]
    assert not out.matches_expected


def test_a_confident_photo_of_something_else_is_also_retaken():
    out, retake = judge(WALL, URI, 0, "te")
    assert retake
    assert out.follow_up == RETAKE["te"]["not_visible"]


def test_after_the_last_retake_it_stops_asking_and_continues_with_a_note():
    out, retake = judge(BLURRY, URI, MAX_RETAKES, "hi")
    assert not retake
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


def test_record_lists_the_photo_on_the_job():
    out, _ = judge(CLEAR, URI, 0, "hi")
    job = record(RepairJob(job_id="j_1"), "r_1", "photo", out)
    assert [(m.request_id, m.uri, m.kind, m.reason) for m in job.media] == [("r_1", URI, "photo", "requested")]


# The session's open requests


def desk():
    sent = []

    async def send(frame):
        sent.append(frame)

    return MediaDesk(send, "gs://media/jobs/j_1/"), sent


def ready(request_id="r_1", uri=URI, kind="photo"):
    return MediaReady(request_id=request_id, uri=uri, kind=kind)


async def test_media_ready_for_an_unknown_or_finished_request_is_rejected():
    d, _ = desk()
    assert not d.ready(ready())
    await d.open("r_1", PCB)
    assert d.ready(ready())
    d.close("r_1")
    assert not d.ready(ready())


async def test_media_ready_outside_this_jobs_folder_or_of_another_kind_is_rejected():
    d, _ = desk()
    await d.open("r_1", PCB)
    assert not d.ready(ready(uri="gs://media/jobs/j_2/a1-photo.jpg"))
    assert not d.ready(ready(uri="gs://other/jobs/j_1/a1-photo.jpg"))
    assert not d.ready(ready(kind="video"))


async def test_open_sends_media_request_to_the_phone():
    d, sent = desk()
    await d.open("r_1", PCB)
    assert sent == [
        MediaRequest(request_id="r_1", kind="photo", target=PCB.target, framing_tip="Flash on", max_seconds=None)
    ]


# The tool as the Live agent calls it


class FakeJobs:
    def __init__(self):
        self.job = RepairJob(job_id="j_1")

    def load(self, job_id):
        return self.job

    def update(self, job_id, change):
        out, self.job = change(self.job)
        return out


def tool_named(tools, name):
    return next(t for t in tools if t.name == name)


def context():
    return SimpleNamespace(state={"job_id": "j_1", "lang": "hi"})


def test_request_media_is_non_blocking_and_answers_when_idle():
    d, _ = desk()
    tool = tool_named(media_tools(d, FakeJobs(), None), "request_media")
    assert tool.behavior == types.Behavior.NON_BLOCKING
    assert tool.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


async def test_blurry_then_clear_retakes_once_on_the_same_request_and_records_the_photo():
    d, sent = desk()
    jobs = FakeJobs()
    checks = iter([BLURRY, CLEAR])

    async def vision(question, uri, schema):
        assert schema is MediaCheck and PCB.target in question
        return next(checks)

    tool = tool_named(media_tools(d, jobs, vision), "request_media")
    call = asyncio.create_task(tool.func(context(), **PCB.model_dump()))
    await asyncio.sleep(0)
    request_id = sent[0].request_id
    assert d.ready(ready(request_id, "gs://media/jobs/j_1/a1-blurry.jpg"))
    await asyncio.sleep(0)
    assert d.ready(ready(request_id))
    out = await call

    results = [f for f in sent if isinstance(f, MediaResult)]
    assert [(r.request_id, r.retake_reason) for r in results] == [
        (request_id, RETAKE["hi"]["blurry"]),
        (request_id, None),
    ]
    assert out["media_uri"] == URI and out["matches_expected"] and out["follow_up"] is None
    assert [m.uri for m in jobs.job.media] == [URI]
    assert not d.ready(ready(request_id))


# confirm_safety takes only the latest photo the server asked for (from T16)


async def test_confirm_safety_rejects_a_photo_no_request_issued_without_calling_vision():
    jobs = FakeJobs()

    async def vision(question, uri, schema):
        raise AssertionError("vision must not run on an unissued photo")

    confirm = tool_named(repair_tools(jobs, vision), "confirm_safety")
    out = await confirm.func(context(), gate_id="G_MAINS_OFF", media_uri=URI)
    assert out["passed"] is False and out["reason"]
    assert jobs.job.gates["G_MAINS_OFF"] == "open"


async def test_confirm_safety_rejects_an_older_photo_and_accepts_the_latest():
    jobs = FakeJobs()
    old, _ = judge(CLEAR, "gs://media/jobs/j_1/old.jpg", 0, "hi")
    new, _ = judge(CLEAR, URI, 0, "hi")
    jobs.job = record(record(jobs.job, "r_1", "photo", old), "r_2", "photo", new)

    async def vision(question, uri, schema):
        return GateCheck(passed=True, reason=None, confidence=0.9)

    confirm = tool_named(repair_tools(jobs, vision), "confirm_safety")
    stale = await confirm.func(context(), gate_id="G_MAINS_OFF", media_uri="gs://media/jobs/j_1/old.jpg")
    assert stale["passed"] is False
    fresh = await confirm.func(context(), gate_id="G_MAINS_OFF", media_uri=URI)
    assert fresh["passed"] is True
    assert jobs.job.gates["G_MAINS_OFF"] == "passed"
