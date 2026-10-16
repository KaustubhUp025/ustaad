"""/ws/live limits (BUILD-GUIDE T27): the 4th Live session is refused, an IP over its rate is refused, and a socket
that goes silent is closed so its Live slot frees (T11 follow-up)."""

import time
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import admission, ws_live
from app.main import app
from app.session import issue

URL = f"/ws/live?token={issue('w_hi_demo', datetime.now(UTC))}&lang=hi&job_id=j_1"


@pytest.fixture(autouse=True)
def live(monkeypatch):
    """A Live model that says nothing until the socket closes; it notes the worker each session is for."""
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    workers = []

    async def live_events(queue, lang, resume, job_id, desk, worker_id):
        workers.append(worker_id)
        while not (await queue.get()).close:
            pass
        return
        yield

    monkeypatch.setattr(ws_live, "live_events", live_events)
    return workers


def test_the_fourth_live_session_gets_rate_limited():
    client = TestClient(app)
    with client.websocket_connect(URL) as a, client.websocket_connect(URL) as b, client.websocket_connect(URL) as c:
        for ws in (a, b, c):
            assert ws.receive_json()["type"] == "session_ready"
        with client.websocket_connect(URL) as d:
            assert d.receive_json() == {"v": 1, "type": "error", "code": "rate_limited", "message": "too many sessions"}
    assert admission.ADMISSION.open_sessions == 0


def test_an_ip_over_its_rate_gets_rate_limited(monkeypatch):
    monkeypatch.setattr(admission, "RATE_PER_MIN", 2)
    client = TestClient(app)
    for _ in range(2):
        with client.websocket_connect(URL) as ws:
            assert ws.receive_json()["type"] == "session_ready"
    with client.websocket_connect(URL) as ws:
        assert ws.receive_json()["code"] == "rate_limited"


def test_a_silent_socket_is_closed_and_frees_its_slot(monkeypatch):
    monkeypatch.setattr(ws_live, "SILENT_CLOSE_S", 0.3)
    with TestClient(app).websocket_connect(URL) as ws:
        assert ws.receive_json()["type"] == "session_ready"
        assert admission.ADMISSION.open_sessions == 1
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    assert admission.ADMISSION.open_sessions == 0


def test_a_pinging_socket_stays_open(monkeypatch):
    monkeypatch.setattr(ws_live, "SILENT_CLOSE_S", 0.3)
    with TestClient(app).websocket_connect(URL) as ws:
        ws.receive_json()
        for _ in range(4):
            time.sleep(0.15)
            ws.send_json({"v": 1, "type": "ping"})
            assert ws.receive_json() == {"v": 1, "type": "pong"}


def test_an_unsigned_token_gets_an_auth_error():
    with TestClient(app).websocket_connect("/ws/live?token=demo&lang=hi&job_id=j_1") as ws:
        assert ws.receive_json()["code"] == "auth"


def test_the_session_is_for_the_worker_the_token_names(live):
    with TestClient(app).websocket_connect(f"/ws/live?token={issue('w_te_demo', datetime.now(UTC))}&lang=te") as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "ping"})
        ws.receive_json()
    assert live == ["w_te_demo"]
