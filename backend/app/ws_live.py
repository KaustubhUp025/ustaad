"""`/ws/live` stub (T09): answers pings, or with MOCK_LIVE=1 replays the recorded G2 session.
The Live bridge to the model replaces the stub in T11."""

import json
import os
import uuid
from asyncio import sleep
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from models.ws import Error, Frame, Ping, Pong, SessionReady, client_frame

router = APIRouter()

FIXTURE = Path(__file__).parents[2] / "seed/fixtures/live_session.jsonl"


async def _send(ws: WebSocket, frame: Frame) -> None:
    await ws.send_text(frame.model_dump_json())


async def _replay(ws: WebSocket) -> None:
    at_ms = 0
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        await sleep((entry["t_ms"] - at_ms) / 1000)
        at_ms = entry["t_ms"]
        await ws.send_json(entry["frame"])


@router.websocket("/ws/live")
async def ws_live(ws: WebSocket, token: str = "") -> None:
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
        else:
            session_id = f"s_{uuid.uuid4().hex[:8]}"
            live_model = os.getenv("LIVE_MODEL", "unset")
            await _send(ws, SessionReady(session_id=session_id, live_model=live_model, resumable=False))
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            text = message.get("text")
            if text is None:
                continue
            try:
                frame = client_frame.validate_json(text)
            except ValidationError:
                await _send(ws, Error(code="bad_request", message="not a v1 client frame"))
                continue
            if isinstance(frame, Ping):
                await _send(ws, Pong())
    except WebSocketDisconnect:
        pass
