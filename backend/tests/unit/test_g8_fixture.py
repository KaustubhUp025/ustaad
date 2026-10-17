import json
from pathlib import Path

from pydantic import TypeAdapter

from models.ws import StepCard, WsServerFrame

FIXTURE = Path(__file__).parents[3] / "seed" / "fixtures" / "live_session_general.jsonl"


def test_g8_replays_a_general_step_only_after_the_mains_gate_passes():
    frames = [TypeAdapter(WsServerFrame).validate_python(json.loads(line)["frame"]) for line in FIXTURE.open()]
    types = [f.type for f in frames]
    assert types.index("safety_gate") < types.index("gate_result") < types.index("step_card")
    steps = [f for f in frames if isinstance(f, StepCard)]
    assert [(s.source.kind, s.source.audio_uri, s.hazard) for s in steps] == [("general", None, "none")]
