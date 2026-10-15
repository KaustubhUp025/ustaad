"""`/ws/live`: the phone's voice line to Ustaad (ws-events.md). Audio and frames go up to the Live
model through ADK and come back down; with MOCK_LIVE=1 the recorded G2 session is replayed instead."""

import json
import logging
import os
import uuid
from asyncio import create_task, sleep
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.cloud import firestore
from google.genai import types
from pydantic import ValidationError

from agent.media_tools import MediaDesk
from agent.ustaad import build_ustaad
from app.live_events import to_frames
from clients.firestore import JobStore
from models.ws import (
    Error,
    Frame,
    MediaCancel,
    MediaOffer,
    MediaReady,
    Ping,
    Pong,
    Ptt,
    SafetyGate,
    SessionReady,
    Text,
    client_frame,
)

router = APIRouter()
logger = logging.getLogger(__name__)

FIXTURE = Path(__file__).parents[2] / "seed/fixtures/live_session.jsonl"
# Each job's open photo requests, kept across reconnects to this instance (session affinity routes them here).
DESKS: dict[str, MediaDesk] = {}
APP = "ustaad"
# Speech code, and the wording the instruction uses: naming the script keeps captions out of Latin letters.
LANGS = {
    "hi": ("hi-IN", "Hindi, written in Devanagari script"),
    "te": ("te-IN", "Telugu, written in Telugu script"),
    "ta": ("ta-IN", "Tamil, written in Tamil script"),
    "bn": ("bn-IN", "Bengali, written in Bengali script"),
    "en": ("en-IN", "English"),
}


async def live_events(
    queue: LiveRequestQueue, lang: str, resume: str | None, job_id: str, desk: MediaDesk
) -> AsyncIterator[Event]:
    """One Live session with the model. Unit tests replace this with a fake."""
    speech_code, language_name = LANGS[lang]
    jobs = JobStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))
    runner = InMemoryRunner(
        agent=build_ustaad(os.environ["LIVE_MODEL"], os.environ["LIVE_LOCATION"], jobs, desk), app_name=APP
    )
    # The repair tools and the gate callback read the job from here; the model never chooses it.
    session = await runner.session_service.create_session(
        app_name=APP, user_id="demo", state={"language_name": language_name, "lang": lang, "job_id": job_id}
    )
    config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(language_code=speech_code),
        # Push-to-talk marks the turn itself, so the model does not wait to hear silence (T05).
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
        ),
        session_resumption=types.SessionResumptionConfig(handle=resume),
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
    )
    async for event in runner.run_live(
        user_id="demo", session_id=session.id, live_request_queue=queue, run_config=config
    ):
        yield event


async def _send(ws: WebSocket, frame: Frame) -> None:
    await ws.send_text(frame.model_dump_json())


async def _replay(ws: WebSocket) -> None:
    at_ms = 0
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        await sleep((entry["t_ms"] - at_ms) / 1000)
        at_ms = entry["t_ms"]
        await ws.send_json(entry["frame"])


async def _downstream(
    ws: WebSocket, queue: LiveRequestQueue, lang: str, resume: str | None, job_id: str, desk: MediaDesk
) -> None:
    partials: dict[str, str] = {}
    try:
        async for event in live_events(queue, lang, resume, job_id, desk):
            for item in to_frames(event, partials):
                if isinstance(item, bytes):
                    await ws.send_bytes(item)
                else:
                    await _send(ws, item)
                # The server, not the model, opens the gate's photo request (Ustaad did for 1 of 5 gates, Oct 15).
                if isinstance(item, SafetyGate):
                    await desk.open_gate(item.gate_id)
    except WebSocketDisconnect:
        pass
    except Exception:  # whatever the Live session died of, the phone gets the contract's one answer
        logger.exception("live session failed")
        await _send(ws, Error(code="live_unavailable", message="Live model unavailable"))
        await ws.close(code=1011)


async def _upstream(ws: WebSocket, queue: LiveRequestQueue | None, desk: MediaDesk | None) -> None:
    """Reads the phone's frames until it disconnects. `queue` and `desk` are None in mock mode: only pings are
    answered."""
    talking = False
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            return
        audio = message.get("bytes")
        if audio is not None:
            if talking:
                queue.send_realtime(types.Blob(data=audio, mime_type="audio/pcm;rate=16000"))
            continue
        try:
            frame = client_frame.validate_json(message["text"])
        except ValidationError:
            await _send(ws, Error(code="bad_request", message="not a v1 client frame"))
            continue
        if isinstance(frame, Ping):
            await _send(ws, Pong())
        elif queue is None:
            continue
        elif isinstance(frame, Ptt):
            talking = frame.state == "start"
            if talking:
                queue.send_activity_start()
            else:
                queue.send_activity_end()
        elif isinstance(frame, Text):
            queue.send_content(types.Content(role="user", parts=[types.Part(text=frame.text)]))
        elif isinstance(frame, MediaOffer):
            await desk.offer(frame.kind)
        elif isinstance(frame, MediaReady | MediaCancel):
            taken = desk.ready(frame) if isinstance(frame, MediaReady) else desk.cancel(frame)
            if not taken:
                await _send(ws, Error(code="bad_request", message="no open media request with that id"))


@router.websocket("/ws/live")
async def ws_live(
    ws: WebSocket, token: str = "", lang: str = "hi", resume: str | None = None, job_id: str = ""
) -> None:
    await ws.accept()
    origin = ws.headers.get("origin")
    allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    # Browsers always send Origin; clients without one (tests, native) are held to the token alone.
    if not token or (origin and origin not in allowed):
        await _send(ws, Error(code="auth", message="missing token or origin not allowed"))
        await ws.close(code=1008)
        return
    try:
        if os.getenv("MOCK_LIVE") == "1":
            await _replay(ws)
            await _upstream(ws, None, None)
            return
        session_id = f"s_{uuid.uuid4().hex[:8]}"
        job_id = job_id or f"j_{uuid.uuid4().hex[:8]}"
        await _send(ws, SessionReady(session_id=session_id, live_model=os.getenv("LIVE_MODEL", "unset"), resumable=True))
        queue = LiveRequestQueue()
        # A photo request belongs to the job, not to this socket: a reconnect picks up its open requests.
        desk = DESKS.setdefault(job_id, MediaDesk(job_id, os.getenv("MEDIA_BUCKET", "")))
        if not resume:
            desk.forget_session()
        desk.attach(lambda frame: _send(ws, frame), queue, lang)
        down = create_task(_downstream(ws, queue, lang, resume, job_id, desk))
        try:
            await _upstream(ws, queue, desk)
        finally:
            desk.detach()
            if desk.idle:
                DESKS.pop(job_id, None)
            queue.close()
            down.cancel()
    except WebSocketDisconnect:
        pass
