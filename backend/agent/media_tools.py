"""request_media as the Live agent calls it (BUILD-GUIDE T17). The tool only opens a request: it is long-running
and NON_BLOCKING, so Ustaad keeps talking while the worker walks to the unit. The job's MediaDesk then answers the
model's call once per checked photo (a retake reason, then the findings), always over the current connection, so a
dropped and resumed session still gets the answer. Measured on gemini-3.8-live (Oct 15): a resumed session takes
the answer to a call made before the drop, and a second answer on the same call is spoken too."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from clients.firestore import JobStore
from models.repair import GateId, MediaKind
from models.tools import ConfirmSafetyIn, GateCheck, MediaCheck, RequestMediaIn, RequestMediaOut
from models.ws import Frame, GateResult, MediaCancel, MediaReady, MediaRequest, MediaResult
from tools import repair
from tools import request_media as rules
from tools.gates import QUESTIONS

ReadPhoto = Callable[[str, str, type], Awaitable[Any]]
Send = Callable[[Frame], Awaitable[None]]


@dataclass
class OpenRequest:
    request_id: str
    call_id: str
    inp: RequestMediaIn
    lang: str
    retakes: int = 0


class MediaDesk:
    """One job's open requests. They outlive a WebSocket: a reconnect attaches the new connection and the phone gets
    the open requests again. Only an open request takes a photo, and only from this job's upload folder, so the model
    cannot reuse an old photo and the phone cannot point vision at another object."""

    def __init__(self, job_id: str, bucket: str) -> None:
        self.job_id = job_id
        # POST /api/media/upload-url puts a job's photos under jobs/<job_id>/.
        self._prefix = f"gs://{bucket}/jobs/{job_id}/"
        self._open: dict[str, OpenRequest] = {}
        self._held: list[types.FunctionResponse] = []
        self._send: Send | None = None
        self._queue: LiveRequestQueue | None = None
        self.on_photo: Callable[[OpenRequest, str], Awaitable[None]] | None = None
        self.tasks: set[asyncio.Task] = set()

    def attach(self, send: Send, queue: LiveRequestQueue) -> None:
        self._send, self._queue = send, queue
        for answer in self._held:
            self._to_model(answer)
        self._held.clear()
        for request in self._open.values():
            self._spawn(self._send(self._frame(request)))

    def detach(self) -> None:
        self._send = self._queue = None

    @property
    def idle(self) -> bool:
        return not self._open and not self._held

    async def open(self, request: OpenRequest) -> None:
        self._open[request.request_id] = request
        if self._send:
            await self._send(self._frame(request))

    def ready(self, frame: MediaReady) -> bool:
        request = self._open.get(frame.request_id)
        if not request or request.inp.kind != frame.kind or not frame.uri.startswith(self._prefix):
            return False
        self._spawn(self.on_photo(request, frame.uri))
        return True

    def cancel(self, frame: MediaCancel) -> bool:
        request = self._open.get(frame.request_id)
        if not request:
            return False
        out = RequestMediaOut(media_uri=None, findings=[], matches_expected=False, confidence=0, follow_up=rules.CANCELLED)
        self.answer(request, out.model_dump(mode="json"), done=True)
        return True

    async def show(self, frame: Frame) -> None:
        """A frame for the phone; dropped while disconnected, since the phone gets the open requests again."""
        if self._send:
            await self._send(frame)

    def answer(self, request: OpenRequest, response: dict, done: bool) -> None:
        """Answers the model's call for this request, delivered when Ustaad is idle; held while disconnected."""
        if done:
            del self._open[request.request_id]
        answer = types.FunctionResponse(
            id=request.call_id,
            name="request_media",
            response=response,
            scheduling=types.FunctionResponseScheduling.WHEN_IDLE,
        )
        if self._queue:
            self._to_model(answer)
        else:
            self._held.append(answer)

    def _to_model(self, answer: types.FunctionResponse) -> None:
        self._queue.send_content(types.Content(role="user", parts=[types.Part(function_response=answer)]))

    @staticmethod
    def _frame(request: OpenRequest) -> MediaRequest:
        return MediaRequest(
            request_id=request.request_id,
            kind=request.inp.kind,
            target=request.inp.target,
            framing_tip=request.inp.framing_tip,
            max_seconds=15 if request.inp.kind == "video" else None,
        )

    def _spawn(self, work: Awaitable[None]) -> None:
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
        change your next step. `target`: what to capture, in his language. `framing_tip`: how, e.g. "Flash on, 20 cm
        door". For a SAFETY_GATE pass its `gate_id`: only that photo opens the gate. You can keep talking while he
        takes it. The result comes later, once per photo: when `retaking` is true, tell him the `follow_up` reason
        briefly; his retake arrives on its own, so do not ask again with this tool. Otherwise use the findings, or
        do what `follow_up` says."""
        inp = RequestMediaIn(kind=kind, target=target, reason=reason, framing_tip=framing_tip, gate_id=gate_id)
        request_id = f"r_{uuid4().hex[:8]}"
        await desk.open(OpenRequest(request_id, tool_context.function_call_id, inp, tool_context.state["lang"]))

    async def on_photo(request: OpenRequest, uri: str) -> None:
        if request.inp.gate_id:
            await _gate_photo(request, uri)
            return
        check = await read_photo(rules.question(request.inp), uri, MediaCheck)
        out, retake = rules.judge(check, uri, request.retakes, request.lang)
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
            jobs.update(desk.job_id, lambda job: (None, _record(job, request, uri, out.findings, out.confidence)))
        desk.answer(request, out.model_dump(mode="json"), done=not retake)

    async def _gate_photo(request: OpenRequest, uri: str) -> None:
        """The gate check alone judges a gate photo, with no retake limit: the gate stays locked until one passes."""
        gate_id = request.inp.gate_id
        check = await read_photo(QUESTIONS[gate_id], uri, GateCheck)

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
        desk.answer(request, response, done=out.passed)

    def _record(job, request: OpenRequest, uri: str, findings, confidence: float):
        return rules.record(job, request.request_id, request.inp.kind, uri, findings, confidence)

    desk.on_photo = on_photo
    tool = FunctionTool(request_media)
    tool.behavior = types.Behavior.NON_BLOCKING
    tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    # Long-running: returning None sends no automatic answer; the desk answers the call later.
    tool.is_long_running = True
    return [tool]
