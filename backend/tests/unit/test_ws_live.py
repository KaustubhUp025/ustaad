import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from google.adk.events import Event
from google.genai import types

from app import ws_live
from app.main import app
from app.session import issue
from models.repair import RepairJob
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


def test_a_step_done_tap_reaches_the_jobs_desk(monkeypatch):
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    taps = []

    async def on_step_done(n):
        taps.append(n)

    desk = ws_live.MediaDesk("j_tap", "media")
    desk.on_step_done = on_step_done
    monkeypatch.setitem(ws_live.DESKS, "j_tap", desk)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_tap") as ws:
        ws.receive_json()
        ws.send_json({"v": 1, "type": "step_done", "n": 3})
        ws.send_json({"v": 1, "type": "ping"})
        assert ws.receive_json()["type"] == "pong"
    assert taps == [3]


def _step(source="general"):
    label = "General guidance" if source == "general" else "Ramesh"
    return {"n": 1, "instruction": "मशीन से जुड़ी पानी की सप्लाई का नल चेक करें कि वह खुला है या नहीं।", "hazard": "none", "source": {"kind": source, "label": label, "audio_uri": None, "doc": None, "page": None}}


def _audio():
    return Event(author="ustaad", content=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x02", mime_type="audio/pcm"))]))


def _say(text, partial=True):
    return Event(author="ustaad", output_transcription=types.Transcription(text=text), partial=partial)


def _session(monkeypatch, job_id, job, events):
    """A desk whose job is `job`, a model that yields `events` then waits, and the notes Ustaad was sent."""
    monkeypatch.delenv("MOCK_LIVE", raising=False)
    desk = ws_live.MediaDesk(job_id, "media")
    desk.load_job = lambda: RepairJob.model_validate(job)
    monkeypatch.setitem(ws_live.DESKS, job_id, desk)
    told = []

    async def live_events(queue, lang, resume, job_id, desk, worker_id):
        for event in events:
            yield event
        while not (req := await queue.get()).close:
            if req.content:
                told.append(req.content.parts[0].text)

    monkeypatch.setattr(ws_live, "live_events", live_events)
    return told


def _until_pong(ws):
    """Every frame the phone gets until a pong: bytes as b"audio", frames by type."""
    ws.send_json({"v": 1, "type": "ping"})
    got = []
    while True:
        message = ws.receive()
        if message.get("bytes") is not None:
            got.append("audio")
            continue
        frame = json.loads(message["text"])
        if frame["type"] == "pong":
            return got
        got.append(frame["type"])


def test_a_step_said_before_next_step_is_cut_off(monkeypatch):
    """Q1-type (Oct 18) on a job with no gate before the step: the rest of the turn is cut and Ustaad is told."""
    told = _session(
        monkeypatch,
        "j_ahead",
        {"job_id": "j_ahead", "steps": [_step("whatsapp_voice")]},
        [_audio(), _say("हम कुछ सामान्य जाँच कर सकते हैं। "), _say("क्या आप चेक कर सकते हैं कि मशीन से जुड़ी पानी की सप्लाई"), _audio(), _say(" का नल खुला है"), Event(author="ustaad", interrupted=True)],
    )
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_ahead") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["audio", "caption", "interrupted", "interrupted"]
    assert told == [ws_live.AHEAD_NOTE]


GATED = {"job_id": "j_gate_hold", "steps": [_step()]}  # a general job: G_MAINS_OFF stands before step 1


def test_while_a_gate_is_open_gate_talk_plays_once_the_turn_is_complete(monkeypatch):
    told = _session(
        monkeypatch,
        "j_gate_hold",
        GATED,
        [_audio(), _say("कृपया मशीन का पावर प्लग "), _audio(), _say("कृपया मशीन का पावर प्लग निकाल दें और उसकी फोटो भेजें।", partial=False), Event(author="ustaad", turn_complete=True)],
    )
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["audio", "caption", "audio", "caption", "turn_complete"]
    assert told == []


def test_while_a_gate_is_open_repair_talk_is_never_played(monkeypatch):
    """c1's case (Oct 18): a terminal-box check from the card's root cause, said while the gate was locked."""
    told = _session(
        monkeypatch,
        "j_gate_hold",
        GATED,
        [_audio(), _say("Outdoor unit ka cover khol kar communication wire check karo", partial=False), Event(author="ustaad", turn_complete=True)],
    )
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["turn_complete"]
    assert told == [ws_live.GATE_NOTE]


def test_while_a_gate_is_open_a_failing_judge_drops_the_turn(monkeypatch):
    """Fail closed (Samyak): if judging the held turn fails, nothing of it is played."""
    told = _session(
        monkeypatch,
        "j_gate_hold",
        GATED,
        [_audio(), _say("कृपया मशीन का पावर प्लग निकाल दें और उसकी फोटो भेजें।", partial=False), Event(author="ustaad", turn_complete=True)],
    )

    def broken(said, job, gate):
        raise RuntimeError("judge failed")

    monkeypatch.setattr(ws_live, "releasable", broken)
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["turn_complete"]
    assert told == [ws_live.GATE_NOTE]


def test_while_a_gate_is_open_a_turn_with_no_caption_is_dropped(monkeypatch):
    told = _session(monkeypatch, "j_gate_hold", GATED, [_audio(), _audio(), Event(author="ustaad", turn_complete=True)])
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["turn_complete"]
    assert told == [ws_live.GATE_NOTE]


def test_while_a_gate_is_open_an_interrupted_turn_is_dropped(monkeypatch):
    _session(monkeypatch, "j_gate_hold", GATED, [_audio(), _say("कृपया मशीन का"), Event(author="ustaad", interrupted=True)])
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["interrupted"]


def test_on_a_general_job_a_spoken_power_on_check_gets_the_stop_screen(monkeypatch):
    passed = {**GATED, "gates": {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "open"}}
    _session(monkeypatch, "j_gate_hold", passed, [_audio(), _say("अब TV ऑन करके देखिए", partial=False), Event(author="ustaad", turn_complete=True)])
    with TestClient(app).websocket_connect(f"/ws/live?token={TOKEN}&lang=hi&job_id=j_gate_hold") as ws:
        ws.receive_json()
        assert _until_pong(ws) == ["audio", "caption", "safety_stop", "turn_complete"]
