import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from google.adk.events import Event
from google.genai import types

from app import ws_live
from app.main import app
from app.session import issue
from models.ws import server_frame

FRAMES = [json.loads(line) for line in ws_live.FIXTURE.read_text(encoding="utf-8").splitlines()]
TOKEN = issue("w_hi_demo", datetime.now(UTC))
URL = f"/ws/live?token={TOKEN}&lang=hi&job_id=j_1"


@pytest.fixture(autouse=True)
def fake_live(monkeypatch):
    """Stands in for the Live model: echoes audio, and answers the end of a spoken turn or a typed line."""
    opened = []

    async def live_events(queue, lang, resume, job_id, desk, worker_id):
        opened.append((lang, resume))
        if lang == "xx":
            raise RuntimeError("model not found")
        while True:
            req = await queue.get()
            if req.close:
                return
            if req.blob:
                yield Event(author="ustaad", content=types.Content(parts=[types.Part(inline_data=req.blob)]))
            if req.activity_end or req.content:
                text = req.content.parts[0].text if req.content else "theek hai"
                yield Event(author="ustaad", output_transcription=types.Transcription(text=text), partial=False)
                yield Event(author="ustaad", turn_complete=True)

    monkeypatch.setattr(ws_live, "live_events", live_events)
    return opened


@pytest.fixture
def mock_live(monkeypatch):
    slept = []

    async def no_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setenv("MOCK_LIVE", "1")
    monkeypatch.setattr(ws_live, "sleep", no_sleep)
    return slept


def test_session_ready_is_the_first_frame(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    monkeypatch.setenv("LIVE_MODEL", "some-live-model")
    with TestClient(app).websocket_connect(URL) as ws:
        first = ws.receive_json()
    assert first["type"] == "session_ready"
    assert first["live_model"] == "some-live-model"


def test_ping_gets_pong_and_unknown_type_gets_bad_request(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(URL) as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "ping"})
        assert ws.receive_json() == {"v": 1, "type": "pong"}
        ws.send_json({"v": 1, "type": "nope"})
        assert ws.receive_json()["code"] == "bad_request"
        ws.send_bytes(b"\x00\x00")
        ws.send_json({"v": 1, "type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_missing_token_gets_auth_error(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect("/ws/live") as ws:
        assert ws.receive_json()["code"] == "auth"


def test_foreign_origin_gets_auth_error(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")
    with TestClient(app).websocket_connect(URL, headers={"origin": "https://evil.example"}) as ws:
        assert ws.receive_json()["code"] == "auth"


def test_mock_live_replays_the_fixture_in_order(mock_live):
    with TestClient(app).websocket_connect(URL) as ws:
        got = [ws.receive_json() for _ in FRAMES]
    assert got == [entry["frame"] for entry in FRAMES]
    assert all(s >= 0 for s in mock_live)
    assert sum(mock_live) == pytest.approx(FRAMES[-1]["t_ms"] / 1000)


def test_fixture_frames_follow_the_contract():
    for entry in FRAMES:
        assert server_frame.validate_python(entry["frame"]).model_dump() == entry["frame"]
    assert FRAMES[0]["frame"]["type"] == "session_ready"


def test_fixture_is_the_g2_script():
    seen = [f["frame"]["type"] for f in FRAMES if f["frame"]["type"] not in ("caption", "turn_complete")]
    assert seen == [
        "session_ready",
        "identified",
        "step_card",
        "media_request",
        "media_result",
        "media_result",
        "safety_gate",
        "gate_result",
        "step_card",
    ]
    results = [f["frame"] for f in FRAMES if f["frame"]["type"] == "media_result"]
    assert results[0]["retake_reason"] and not results[0]["matches_expected"]
    assert results[1]["retake_reason"] is None and results[1]["matches_expected"]


def test_fixture_shows_no_hazardous_step_before_its_gate_passes():
    needs = {"none": set(), "HV": {"G_MAINS_OFF"}, "capacitor": {"G_MAINS_OFF", "G_CAP_DISCHARGE"}}
    passed = set()
    for frame in (entry["frame"] for entry in FRAMES):
        if frame["type"] == "gate_result" and frame["passed"]:
            passed.add(frame["gate_id"])
        if frame["type"] == "step_card":
            assert needs[frame["hazard"]] <= passed


def test_spoken_turn_reaches_the_model_and_its_reply_reaches_the_phone(monkeypatch, fake_live):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=te&resume=h0") as ws:
        assert ws.receive_json()["resumable"] is True
        ws.send_bytes(b"dropped: not inside ptt")
        ws.send_json({"v": 1, "type": "ptt", "state": "start"})
        ws.send_bytes(b"\x01\x02")
        ws.send_json({"v": 1, "type": "ptt", "state": "end"})
        assert ws.receive_bytes() == b"\x01\x02"
        assert ws.receive_json() == {"v": 1, "type": "caption", "who": "ustaad", "text": "theek hai", "final": True}
        assert ws.receive_json() == {"v": 1, "type": "turn_complete"}
    assert fake_live == [("te", "h0")]


def test_typed_text_is_a_turn(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(URL) as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "text", "text": "PCB nahi hai"})
        assert ws.receive_json()["text"] == "PCB nahi hai"
        assert ws.receive_json()["type"] == "turn_complete"


def test_live_failure_is_reported_as_live_unavailable(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=xx") as ws:
        assert ws.receive_json()["type"] == "session_ready"
        assert ws.receive_json()["code"] == "live_unavailable"


def test_mock_live_never_opens_a_model_session(mock_live, fake_live):
    with TestClient(app).websocket_connect(URL) as ws:
        ws.receive_json()
    assert fake_live == []


def test_media_ready_for_an_unknown_request_gets_bad_request(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(URL) as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "media_ready", "request_id": "r_9", "uri": "gs://b/jobs/j_1/x.jpg", "kind": "photo"})
        assert ws.receive_json()["code"] == "bad_request"


def test_a_safety_gate_from_the_model_opens_its_photo_request(monkeypatch):
    """The gate photo request comes from the server as soon as the gate frame goes out, not from the model."""
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    gate = {"status": "SAFETY_GATE", "gate_id": "G_MAINS_OFF", "required_evidence": "MCB OFF photo"}

    async def live_events(queue, lang, resume, job_id, desk, worker_id):
        response = types.FunctionResponse(name="next_step", response=gate)
        yield Event(author="ustaad", content=types.Content(parts=[types.Part(function_response=response)]))
        while not (await queue.get()).close:
            pass

    monkeypatch.setattr(ws_live, "live_events", live_events)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate") as ws:
        ws.receive_json()
        assert ws.receive_json()["type"] == "safety_gate"
        request = ws.receive_json()
        assert (request["type"], request["kind"], request["framing_tip"]) == ("media_request", "photo", "")


def test_media_offer_gets_a_media_request_from_the_server(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_offer") as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "media_offer", "kind": "photo"})
        request = ws.receive_json()
        assert (request["type"], request["kind"], request["target"]) == ("media_request", "photo", "")
