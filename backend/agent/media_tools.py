"""request_media as the Live agent calls it (BUILD-GUIDE T17). The tool runs NON_BLOCKING, so Ustaad keeps talking
while the worker walks to the unit; it waits on the session's MediaDesk for the phone's photo, retakes on the same
request ID, and its answer reaches the model WHEN_IDLE."""

import asyncio
from collections.abc import Awaitable, Callable
from uuid import uuid4

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from clients.firestore import JobStore
from models.repair import MediaKind
from models.tools import MediaCheck, RequestMediaIn, RequestMediaOut
from models.ws import Frame, MediaCancel, MediaReady, MediaRequest, MediaResult
from tools import request_media as rules

ReadPhoto = Callable[[str, str, type[MediaCheck]], Awaitable[MediaCheck]]


class MediaDesk:
    """The session's open requests. Only an open request takes a photo, and only from this job's upload folder,
    so the model cannot reuse an old photo and the phone cannot point vision at another object."""

    def __init__(self, send: Callable[[Frame], Awaitable[None]], uri_prefix: str) -> None:
        self.send = send
        self._prefix = uri_prefix
        self._open: dict[str, tuple[MediaKind, asyncio.Queue[str | None]]] = {}

    async def open(self, request_id: str, inp: RequestMediaIn) -> None:
        self._open[request_id] = (inp.kind, asyncio.Queue())
        await self.send(
            MediaRequest(
                request_id=request_id,
                kind=inp.kind,
                target=inp.target,
                framing_tip=inp.framing_tip,
                max_seconds=15 if inp.kind == "video" else None,
            )
        )

    def ready(self, frame: MediaReady) -> bool:
        kind, photos = self._open.get(frame.request_id, (None, None))
        if kind != frame.kind or not frame.uri.startswith(self._prefix):
            return False
        photos.put_nowait(frame.uri)
        return True

    def cancel(self, frame: MediaCancel) -> bool:
        if frame.request_id not in self._open:
            return False
        self._open[frame.request_id][1].put_nowait(None)
        return True

    async def next_photo(self, request_id: str) -> str | None:
        """The next uploaded URI for this request; None when he cancelled."""
        return await self._open[request_id][1].get()

    def close(self, request_id: str) -> None:
        del self._open[request_id]


def media_tools(desk: MediaDesk, jobs: JobStore, read_photo: ReadPhoto) -> list[FunctionTool]:
    async def request_media(tool_context: ToolContext, kind: MediaKind, target: str, reason: str, framing_tip: str) -> dict:
        """Asks him for a photo (or a video, or a photo of a manual page with kind "document") when seeing it would
        change your next step, including the photo a SAFETY_GATE needs. `target`: what to capture, in his
        language. `framing_tip`: how, e.g. "Flash on, 20 cm door". You can keep talking while he takes it; the
        phone asks for retakes itself. Use the `media_uri` you get back for confirm_safety. A `follow_up` says
        what to do when there is no good photo."""
        inp = RequestMediaIn(kind=kind, target=target, reason=reason, framing_tip=framing_tip)
        request_id = f"r_{uuid4().hex[:8]}"
        await desk.open(request_id, inp)
        try:
            for retakes in range(rules.MAX_RETAKES + 1):
                uri = await desk.next_photo(request_id)
                if uri is None:
                    out = RequestMediaOut(
                        media_uri=None, findings=[], matches_expected=False, confidence=0, follow_up=rules.CANCELLED
                    )
                    return out.model_dump(mode="json")
                check = await read_photo(rules.question(inp), uri, MediaCheck)
                out, retake = rules.judge(check, uri, retakes, tool_context.state["lang"])
                await desk.send(
                    MediaResult(
                        request_id=request_id,
                        matches_expected=out.matches_expected,
                        confidence=out.confidence,
                        retake_reason=out.follow_up if retake else None,
                    )
                )
                if not retake:
                    break
        finally:
            desk.close(request_id)
        jobs.update(tool_context.state["job_id"], lambda job: (None, rules.record(job, request_id, kind, out)))
        return out.model_dump(mode="json")

    tool = FunctionTool(request_media)
    tool.behavior = types.Behavior.NON_BLOCKING
    tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return [tool]
