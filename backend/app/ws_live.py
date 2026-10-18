"""`/ws/live`: the phone's voice line to Ustaad (ws-events.md). Audio and frames go up to the Live
model through ADK and come back down; with MOCK_LIVE=1 the recorded G2 session is replayed instead."""

import json
import logging
import os
import uuid
from asyncio import create_task, sleep, to_thread, wait_for
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event
from google.adk.memory import VertexAiMemoryBankService
from google.adk.runners import InMemoryRunner
from google.cloud import firestore
from google.genai import types
from pydantic import ValidationError

from agent.media_tools import MediaDesk, ReadPhoto
from agent.memory import APP, memory_user, recall, remember
from agent.ustaad import build_ustaad
from app import admission
from app.demo_safe import demo_safe
from app.live_events import AHEAD_NOTE, GATE_NOTE, ahead, power_on_stop, to_frames
from app.session import verify
from clients.firestore import CardStore, DemoCacheStore, InventoryStore, JobStore, QuoteStore, WorkerStore
from clients.gemini import read_photo
from clients.manual_search import manual_search_client
from clients.places import places_client
from clients.storage import object_md5
from clients.telegram import telegram_bot
from models.repair import RepairJob
from models.ws import (
    Caption,
    Error,
    Frame,
    Interrupted,
    MediaCancel,
    MediaOffer,
    MediaReady,
    Ping,
    Pong,
    Ptt,
    SafetyGate,
    SafetyStop,
    SessionReady,
    StepDone,
    Text,
    TurnComplete,
    client_frame,
)
from tools.gates import open_gate

router = APIRouter()
logger = logging.getLogger(__name__)

FIXTURE = Path(__file__).parents[2] / "seed/fixtures/live_session.jsonl"
# Each job's open photo requests, kept across reconnects to this instance (session affinity routes them here).
DESKS: dict[str, MediaDesk] = {}
# The phone pings every 20 s; a socket silent this long lost its network, and closing it frees its Live slot (T11).
SILENT_CLOSE_S = 45
# Ustaad's audio to the phone: PCM16 at 24 kHz, mono.
OUT_BYTES_PER_S = 24_000 * 2
# Speech code, and the wording the instruction uses: naming the script keeps captions out of Latin letters.
LANGS = {
    "hi": ("hi-IN", "Hindi, written in Devanagari script"),
    "te": ("te-IN", "Telugu, written in Telugu script"),
    "ta": ("ta-IN", "Tamil, written in Tamil script"),
    "bn": ("bn-IN", "Bengali, written in Bengali script"),
    "en": ("en-IN", "English"),
}


async def live_events(
    queue: LiveRequestQueue,
    lang: str,
    resume: str | None,
    job_id: str,
    desk: MediaDesk,
    worker_id: str,
    token: str,
) -> AsyncIterator[Event]:
    """One Live session with the model. Unit tests replace this with a fake."""
    speech_code, language_name = LANGS[lang]
    db = firestore.Client(database=os.environ["FIRESTORE_DB"])
    jobs = JobStore(db)
    user_id = memory_user(os.environ["FIRESTORE_DB"], worker_id, token)
    memory = (
        VertexAiMemoryBankService(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.getenv("MEMORY_LOCATION", "us-central1"),
            agent_engine_id=os.environ["AGENT_ENGINE_ID"],
        )
        if os.getenv("AGENT_ENGINE_ID")
        else None
    )
    runner = InMemoryRunner(
        agent=build_ustaad(
            os.environ["LIVE_MODEL"],
            os.environ["LIVE_LOCATION"],
            jobs,
            CardStore(db),
            InventoryStore(db),
            QuoteStore(db),
            telegram_bot(),
            WorkerStore(db),
            places_client(),
            desk,
            _photo_reader(db),
            manuals=manual_search_client(),
        ),
        app_name=APP,
    )
    # The repair tools and the gate callback read the job from here; the model never chooses it.
    session = await runner.session_service.create_session(
        app_name=APP,
        user_id=user_id,
        state={
            "language_name": language_name,
            "lang": lang,
            "job_id": job_id,
            "worker_id": worker_id,
            "memory_summary": await recall(memory, user_id) if memory else None,
        },
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
    try:
        async for event in runner.run_live(
            user_id=user_id, session_id=session.id, live_request_queue=queue, run_config=config
        ):
            yield event
    finally:
        # The socket closing cancels this session; what was said is saved for his next one.
        if memory:
            ended = await runner.session_service.get_session(
                app_name=APP, user_id=user_id, session_id=session.id
            )
            await remember(memory, user_id, ended.events)


async def _send(ws: WebSocket, frame: Frame) -> None:
    await ws.send_text(frame.model_dump_json())


def _photo_reader(db: firestore.Client) -> ReadPhoto:
    """With DEMO_SAFE=1, photo checks fall back to recorded answers when Flash is slow (T27); DEMO_MODEL_DELAY_S
    slows Flash on purpose to test that."""
    if os.getenv("DEMO_SAFE") != "1":
        return read_photo
    return demo_safe(read_photo, DemoCacheStore(db), object_md5, float(os.getenv("DEMO_MODEL_DELAY_S", "0")))


def _client_ip(ws: WebSocket) -> str:
    # Cloud Run's front end appends the caller's address to X-Forwarded-For, so the last entry is the real one; the
    # earlier ones are whatever the client sent.
    forwarded = ws.headers.get("x-forwarded-for")
    return forwarded.split(",")[-1].strip() if forwarded else ws.client.host if ws.client else ""


async def _refuse(ws: WebSocket, message: str) -> None:
    await _send(ws, Error(code="rate_limited", message=message))
    await ws.close(code=1013)


async def _replay(ws: WebSocket) -> None:
    at_ms = 0
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        await sleep((entry["t_ms"] - at_ms) / 1000)
        at_ms = entry["t_ms"]
        await ws.send_json(entry["frame"])


async def _downstream(
    ws: WebSocket,
    queue: LiveRequestQueue,
    lang: str,
    resume: str | None,
    job_id: str,
    desk: MediaDesk,
    worker_id: str,
    token: str,
) -> None:
    partials: dict[str, str] = {}
    # Speech guards: the job as last read (read again after a tool answer and at each turn), whether the rest of
    # this turn is cut off, the seconds of audio the phone got this turn (how much he heard before a cut), whether
    # this turn is muted because a gate is open, whether anything of it was dropped, and whether Ustaad was told
    # about this gate's mute: once per gate, since his answer to the note is muted too and would draw another note.
    job: RepairJob | None = None
    cut = False
    heard_s = 0.0
    muted = False
    dropped = False
    noted = False
    try:
        async for event in live_events(queue, lang, resume, job_id, desk, worker_id, token):
            if event.content and any(part.function_response for part in event.content.parts or []):
                job = None
            for item in to_frames(event, partials, lang):
                ustaads = isinstance(item, bytes) or (isinstance(item, Caption) and item.who == "ustaad")
                if isinstance(item, Interrupted | TurnComplete):
                    if dropped and not noted and isinstance(item, TurnComplete):
                        desk.note(GATE_NOTE)
                        noted = True
                    job, cut, heard_s, muted, dropped = None, False, 0.0, False, False
                elif cut and ustaads:
                    continue
                elif ustaads:
                    if not muted:
                        # Fail closed: with no loader, or a job that cannot be read, the gate state is unknown and
                        # nothing of the turn is played.
                        try:
                            if desk.load_job is None:
                                raise LookupError("no job loader")
                            job = job or await to_thread(desk.load_job)
                            muted = open_gate(job) is not None
                            noted = noted and muted
                        except Exception as exc:  # noqa: BLE001 — unknown gate state plays nothing
                            logger.warning("gate mute: job unreadable (%s)", type(exc).__name__)
                            muted = True
                    if muted:
                        dropped = True
                        continue
                    if isinstance(item, Caption):
                        step = ahead(item.text, job)
                        if step:
                            cut = True
                            await _stop_ahead(ws, desk, step.n, heard_s)
                            continue
                        if item.final and power_on_stop(item.text, job):
                            await _send(ws, item)
                            await _send(ws, SafetyStop(reason="power_on", message="Stopped for safety"))
                            continue
                if isinstance(item, bytes):
                    heard_s += len(item) / OUT_BYTES_PER_S
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


async def _stop_ahead(ws: WebSocket, desk: MediaDesk, n: int, heard_s: float) -> None:
    """Ustaad began saying step `n` before next_step handed it out (no gate is open, or the turn would be held): the
    phone stops playing him and he is told to get the step from next_step. The note also ends his turn: new content
    interrupts the Live model's answer. Captions trail the audio, so his first words of the step were heard."""
    logger.info("speech guard: step %d said before next_step, cut after %.1f s of audio", n, heard_s)
    await _send(ws, Interrupted())
    desk.note(AHEAD_NOTE)


async def _upstream(ws: WebSocket, queue: LiveRequestQueue | None, desk: MediaDesk | None) -> None:
    """Reads the phone's frames until it disconnects. `queue` and `desk` are None in mock mode: only pings are
    answered."""
    talking = False
    while True:
        try:
            message = await wait_for(ws.receive(), SILENT_CLOSE_S)
        except TimeoutError:
            await ws.close(code=1001)
            return
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
        elif isinstance(frame, StepDone):
            if desk.on_step_done:
                await desk.on_step_done(frame.n)
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
    # Browsers always send Origin; clients without one (tests, native) are held to the token alone. The worker comes
    # from the signed token (POST /api/demo/session), never from the client.
    worker_id = verify(token, datetime.now(UTC))
    if worker_id is None or (origin and origin not in allowed):
        await _send(ws, Error(code="auth", message="missing token or origin not allowed"))
        await ws.close(code=1008)
        return
    if not admission.ADMISSION.allow(_client_ip(ws)):
        await _refuse(ws, "too many connections")
        return
    try:
        if os.getenv("MOCK_LIVE") == "1":
            await _replay(ws)
            await _upstream(ws, None, None)
            return
        if not admission.ADMISSION.acquire():
            await _refuse(ws, "too many sessions")
            return
        try:
            await _live(ws, lang, resume, job_id, worker_id, token)
        finally:
            admission.ADMISSION.release()
    except WebSocketDisconnect:
        pass


async def _live(
    ws: WebSocket, lang: str, resume: str | None, job_id: str, worker_id: str, token: str
) -> None:
    """One Live session for this socket, holding one of the instance's Live slots."""
    session_id = f"s_{uuid.uuid4().hex[:8]}"
    job_id = job_id or f"j_{uuid.uuid4().hex[:8]}"
    await _send(
        ws, SessionReady(session_id=session_id, live_model=os.getenv("LIVE_MODEL", "unset"), resumable=True)
    )
    queue = LiveRequestQueue()
    # A photo request belongs to the job, not to this socket: a reconnect picks up its open requests.
    desk = DESKS.setdefault(job_id, MediaDesk(job_id, os.getenv("MEDIA_BUCKET", "")))
    if not resume:
        desk.forget_session()
    desk.attach(lambda frame: _send(ws, frame), queue, lang)
    down = create_task(_downstream(ws, queue, lang, resume, job_id, desk, worker_id, token))
    try:
        await _upstream(ws, queue, desk)
    finally:
        desk.detach(queue)
        if desk.idle:
            DESKS.pop(job_id, None)
        queue.close()
        down.cancel()
