"""Photo requests for the Live agent (BUILD-GUIDE T17). A request is opened by Ustaad (request_media) or by the server
when a safety gate stands before the next step; either way the server issues the request ID. The job's MediaDesk
takes the phone's photo for it, checks it, and tells Ustaad once per checked photo: as the answer to his
request_media call, or as a notice when he made no call. Measured on gemini-3.8-live (Oct 15): a resumed session
takes the answer to a call made before the drop; a second answer on the same call is spoken too; Ustaad opened the
gate photo request himself for only 1 of 5 gates, so the server opens it."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from clients.firestore import JobStore
from models.repair import GateId, MediaKind
from models.tools import (
    ConfirmSafetyIn,
    GateCheck,
    MediaCheck,
    RepairDone,
    RequestMediaIn,
    RequestMediaOut,
    SafetyGateOut,
    StepOut,
)
from models.ws import (
    Frame,
    GateResult,
    MediaCancel,
    MediaReady,
    MediaRequest,
    MediaResult,
    SafetyGate,
    StepCard,
)
from tools import repair
from tools import request_media as rules
from tools.gates import EVIDENCE, QUESTIONS, open_gate

ReadPhoto = Callable[[str, str, type], Awaitable[Any]]
Send = Callable[[Frame], Awaitable[None]]
logger = logging.getLogger(__name__)

# Flash photo checks took ~5 s, with outliers up to 26 s (Oct 15); past this the phone asks for the photo again.
VISION_TIMEOUT_S = 30


@dataclass
class OpenRequest:
    request_id: str
    call_id: str | None  # the model's request_media call; None when the server or the worker opened the request
    inp: RequestMediaIn
    lang: str
    retakes: int = 0


def _own_photo_note(out: RequestMediaOut) -> str:
    if not out.matches_expected:
        return f"[Photo from the worker, sent on his own, is still unclear. {out.follow_up}]"
    seen = "; ".join(f"{o.label}: {o.value} ({o.confidence:.2f})" for o in out.findings) or "nothing specific"
    return f"[Photo from the worker, sent on his own; checked by vision] findings: {seen}."


class MediaDesk:
    """One job's open requests. They outlive a WebSocket: a reconnect attaches the new connection and the phone gets
    the open requests again. Only an open request takes a photo, and only from this job's upload folder, so the model
    cannot reuse an old photo and the phone cannot point vision at another object."""

    def __init__(self, job_id: str, bucket: str) -> None:
        self.job_id = job_id
        # POST /api/media/upload-url puts a request's photos under jobs/<job_id>/<request_id>/.
        self._prefix = f"gs://{bucket}/jobs/{job_id}/"
        self._open: dict[str, OpenRequest] = {}
        self._held: list[types.Content] = []
        self._send: Send | None = None
        self._queue: LiveRequestQueue | None = None
        self.lang = "hi"
        self.on_photo: Callable[[OpenRequest, str], Awaitable[None]] | None = None
        self.tasks: set[asyncio.Task] = set()

    def attach(self, send: Send, queue: LiveRequestQueue, lang: str) -> None:
        self._send, self._queue, self.lang = send, queue, lang
        for content in self._held:
            queue.send_content(content)
        self._held.clear()
        for request in self._open.values():
            self.spawn(send(self._frame(request)))

    def forget_session(self) -> None:
        """A new Live session (no resume handle) never made the old session's calls, so their requests and held
        answers go (phone test 3, Oct 15: the phone was asked again for a photo the new Ustaad knew nothing of).
        Gate and worker requests stay; a gate request Ustaad joined is answered with a notice instead."""
        self._held.clear()
        for request in list(self._open.values()):
            if request.inp.gate_id:
                request.call_id = None
            elif request.call_id:
                del self._open[request.request_id]

    def detach(self, queue: LiveRequestQueue) -> None:
        """Only the attached connection lets go: an old socket can end after the phone has reconnected."""
        if self._queue is queue:
            self._send = self._queue = None

    def owns(self, uri: str) -> bool:
        """A photo uploaded for this job. Vision reads nothing else, so the model cannot point it at another object."""
        return uri.startswith(self._prefix)

    @property
    def idle(self) -> bool:
        return self._queue is None and not self._open and not self._held

    async def open(self, request: OpenRequest) -> None:
        self._open[request.request_id] = request
        await self.show(self._frame(request))

    async def open_gate(self, gate_id: GateId) -> None:
        """Opens the photo request for a gate that stands before the next step, unless one is open already."""
        if self._gate_request(gate_id):
            return
        inp = RequestMediaIn(kind="photo", target=EVIDENCE[gate_id], reason="safety gate", framing_tip="", gate_id=gate_id)
        await self.open(OpenRequest(f"r_{uuid4().hex[:8]}", None, inp, self.lang))

    async def offer(self, kind: Literal["photo", "document"]) -> None:
        """He wants to send a photo himself. An open gate request takes it first, then a request from Ustaad (the
        phone gets that request again); otherwise a new request with no target, judged only for readability."""
        open_requests = list(self._open.values())
        request = next((r for r in open_requests if r.inp.gate_id), None) or next(reversed(open_requests), None)
        if request:
            await self.show(self._frame(request))
            return
        inp = RequestMediaIn(kind=kind, target="", reason="worker", framing_tip="")
        await self.open(OpenRequest(f"r_{uuid4().hex[:8]}", None, inp, self.lang))

    def join_gate(self, gate_id: GateId, call_id: str) -> bool:
        """Ustaad asked for a gate photo the server already asked for: his call gets that request's answer."""
        request = self._gate_request(gate_id)
        if request is None or request.call_id is not None:
            return False
        request.call_id = call_id
        return True

    def ready(self, frame: MediaReady) -> bool:
        request = self._open.get(frame.request_id)
        # Only this request's folder: a photo uploaded for an earlier request cannot answer it (PR #25 review).
        if not request or request.inp.kind != frame.kind or not frame.uri.startswith(f"{self._prefix}{request.request_id}/"):
            return False
        self.spawn(self.on_photo(request, frame.uri))
        return True

    def cancel(self, frame: MediaCancel) -> bool:
        request = self._open.get(frame.request_id)
        if not request:
            return False
        out = RequestMediaOut(media_uri=None, findings=[], matches_expected=False, confidence=0, follow_up=rules.CANCELLED)
        self.answer(request, out.model_dump(mode="json"), done=True, notice=f"[He closed the photo request: {out.follow_up}]")
        return True

    async def show(self, frame: Frame) -> None:
        """A frame for the phone; dropped while disconnected, since the phone gets the open requests again."""
        if self._send:
            await self._send(frame)

    def answer(self, request: OpenRequest, response: dict, done: bool, notice: str | None) -> None:
        """Tells Ustaad about this request when he is idle: the answer to his call, or `notice` when he made none
        (nothing when `notice` is None). Held while disconnected."""
        if done:
            del self._open[request.request_id]
        if request.call_id:
            answer = types.FunctionResponse(
                id=request.call_id,
                name="request_media",
                response=response,
                scheduling=types.FunctionResponseScheduling.WHEN_IDLE,
            )
            content = types.Content(role="user", parts=[types.Part(function_response=answer)])
        elif notice:
            content = types.Content(role="user", parts=[types.Part(text=notice)])
        else:
            return
        if self._queue:
            self._queue.send_content(content)
        else:
            self._held.append(content)

    def _gate_request(self, gate_id: GateId) -> OpenRequest | None:
        return next((r for r in self._open.values() if r.inp.gate_id == gate_id), None)

    @staticmethod
    def _frame(request: OpenRequest) -> MediaRequest:
        return MediaRequest(
            request_id=request.request_id,
            kind=request.inp.kind,
            target=request.inp.target,
            framing_tip=request.inp.framing_tip,
            max_seconds=15 if request.inp.kind == "video" else None,
        )

    def spawn(self, work: Awaitable[None]) -> None:
        task = asyncio.ensure_future(work)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


def media_tools(desk: MediaDesk, jobs: JobStore, read_photo: ReadPhoto) -> list[FunctionTool]:
    async def request_media(
        tool_context: ToolContext,
        kind: MediaKind,
        target: str,
        reason: str,
        framing_tip: str,
        gate_id: GateId | None = None,
    ) -> None:
        """Asks him for a photo (or a video, or with kind "document" a photo of a manual page) when seeing it would
        change your next step. `target`: what to capture. `framing_tip`: how to hold or light it. Both show on his
        screen beside the app's own words, so write them in his language's own script (Hindi in Devanagari, Telugu
        in Telugu script), never in Roman letters unless he speaks English. A SAFETY_GATE's photo is asked for already; do not ask for it here. You can keep talking while he
        takes it. The result comes later, once per photo: when `retaking` is true, tell him the `follow_up` reason
        briefly; his retake arrives on its own, so do not ask again with this tool. Otherwise use the findings, or
        do what `follow_up` says."""
        if gate_id and desk.join_gate(gate_id, tool_context.function_call_id):
            return
        inp = RequestMediaIn(kind=kind, target=target, reason=reason, framing_tip=framing_tip, gate_id=gate_id)
        request_id = f"r_{uuid4().hex[:8]}"
        await desk.open(OpenRequest(request_id, tool_context.function_call_id, inp, tool_context.state["lang"]))

    async def on_photo(request: OpenRequest, uri: str) -> None:
        schema = GateCheck if request.inp.gate_id else MediaCheck
        question = QUESTIONS[request.inp.gate_id] if request.inp.gate_id else rules.question(request.inp)
        try:
            check = await asyncio.wait_for(read_photo(question, uri, schema), VISION_TIMEOUT_S)
        except Exception:  # quota, network or a hung call: the request stays open and he sends the photo again
            logger.exception("photo check failed")
            await desk.show(
                MediaResult(
                    request_id=request.request_id,
                    matches_expected=False,
                    confidence=0,
                    retake_reason=rules.NOT_CHECKED[request.lang],
                )
            )
            return
        if request.inp.gate_id:
            await _gate_photo(request, uri, check)
        else:
            await _photo(request, uri, check)

    async def _photo(request: OpenRequest, uri: str, check: MediaCheck) -> None:
        own = not request.inp.target
        out, retake = rules.judge(check, uri, request.retakes, request.lang, own)
        request.retakes += retake
        await desk.show(
            MediaResult(
                request_id=request.request_id,
                matches_expected=out.matches_expected,
                confidence=out.confidence,
                retake_reason=out.follow_up if retake else None,
            )
        )
        if not retake:
            reason = ("manual" if request.inp.kind == "document" else "side_issue") if own else "requested"
            jobs.update(
                desk.job_id, lambda job: (None, _record(job, request, uri, out.findings, out.confidence, reason))
            )
        # His own photo: Ustaad hears only the final result; the phone shows the retake reasons.
        notice = None if retake or not own else _own_photo_note(out)
        desk.answer(request, out.model_dump(mode="json"), done=not retake, notice=notice)

    async def _gate_photo(request: OpenRequest, uri: str, check: GateCheck) -> None:
        """The gate check alone judges a gate photo, with no retake limit: the gate stays locked until one passes."""
        gate_id = request.inp.gate_id

        def change(job):
            out, job = repair.confirm_safety(ConfirmSafetyIn(gate_id=gate_id, media_uri=uri), job, check)
            return out, _record(job, request, uri, [], check.confidence)

        out = jobs.update(desk.job_id, change)
        await desk.show(GateResult(gate_id=gate_id, passed=out.passed, reason=out.reason))
        await desk.show(
            MediaResult(
                request_id=request.request_id,
                matches_expected=out.passed,
                confidence=check.confidence,
                retake_reason=None if out.passed else rules.GATE_RETAKE[request.lang][gate_id],
            )
        )
        response = out.model_dump(mode="json") | {"media_uri": uri, "retaking": not out.passed}
        if not out.passed:
            notice = f"[Safety check photo for gate {gate_id} failed: {out.reason} He will send another; tell him why.]"
            desk.answer(request, response, done=False, notice=notice)
            return
        # The server hands out what comes next, through the same gate-checked next_step, so the step card always
        # shows and Ustaad says the step it handed out (he called next_step himself for only 3 of 5 passes, Oct 15).
        after = jobs.update(desk.job_id, repair.next_step)
        notice = await _hand_out(gate_id, after)
        desk.answer(request, response | {"next": after.model_dump(mode="json")}, done=True, notice=notice)

    async def _hand_out(gate_id: GateId, after: StepOut | SafetyGateOut | RepairDone) -> str:
        """Shows what next_step returned after a passed gate and returns the note that tells Ustaad."""
        if isinstance(after, StepOut):
            step = after.step
            await desk.show(StepCard(job_id=after.job_id, of=after.of, **step.model_dump()))
            return (
                f"[Safety check {gate_id} passed. The app handed out step {step.n} of {after.of}; it is on his screen: "
                f'"{step.instruction}". Say this step to him now; do not call next_step until he reports back on it.]'
            )
        if isinstance(after, SafetyGateOut):
            await desk.show(
                SafetyGate(gate_id=after.gate_id, message="Safety check first", required_evidence=after.required_evidence)
            )
            await desk.open_gate(after.gate_id)
            return (
                f"[Safety check {gate_id} passed. Another safety check comes before the next step: {after.gate_id}, "
                f"{after.required_evidence}. His phone asks for that photo; tell him what to do. Do not say the step.]"
            )
        return f"[Safety check {gate_id} passed. Every step has been given.]"

    def _record(job, request: OpenRequest, uri: str, findings, confidence: float, reason="requested"):
        return rules.record(job, request.request_id, request.inp.kind, uri, findings, confidence, reason)

    desk.on_photo = on_photo
    async def reopen_gate(gate_id: GateId) -> None:
        # The gate first: with only the request, the phone skips the gate screen (phone test, Oct 17).
        await desk.show(SafetyGate(gate_id=gate_id, message="Safety check first", required_evidence=EVIDENCE[gate_id]))
        await desk.open_gate(gate_id)

    # After a reconnect, possibly on another instance: a gate before the next step needs its photo request again.
    gate = open_gate(jobs.load(desk.job_id))
    if gate:
        desk.spawn(reopen_gate(gate))
    tool = FunctionTool(request_media)
    tool.behavior = types.Behavior.NON_BLOCKING
    tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    # Long-running: returning None sends no automatic answer; the desk answers the call later.
    tool.is_long_running = True
    return [tool]
