"""G1 onboarding replays (T21): live_session_g1*.jsonl were recorded from the real Live model on Oct 18 (text turns,
in-memory stores). Every frame follows the contract, the six answers arrive as six profile_update frames in G1 order,
the last one marks onboarding done, and Ustaad speaks the session's script."""

import json
import re
from pathlib import Path

import pytest

from models.ws import server_frame

FIXTURES = Path(__file__).parents[3] / "seed/fixtures"
SCRIPT = {"hi": r"[ऀ-ॿ]", "te": r"[ఀ-౿]"}
G1_ORDER = [["trades"], ["brands"], ["pincode"], ["experience_yrs"], ["stock"], ["shop", "onboarding_done"]]


def frames(name):
    return [json.loads(line)["frame"] for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize(("name", "lang"), [("live_session_g1.jsonl", "hi"), ("live_session_g1_te.jsonl", "te")])
def test_g1_replay_follows_the_contract_and_fills_the_profile_in_order(name, lang):
    replay = frames(name)
    for frame in replay:
        assert server_frame.validate_python(frame).model_dump() == frame
    updates = [f["fields"] for f in replay if f["type"] == "profile_update"]
    assert [list(u) for u in updates] == G1_ORDER
    assert updates[0]["trades"] == ["ac", "fridge"] and updates[2]["pincode"] == "201301"
    assert updates[-1]["onboarding_done"] is True
    spoken = [f["text"] for f in replay if f["type"] == "caption" and f["who"] == "ustaad"]
    assert len(spoken) == 7 and all(re.search(SCRIPT[lang], s) for s in spoken)
