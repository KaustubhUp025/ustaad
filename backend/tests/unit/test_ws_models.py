import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.ws import client_frame, server_frame

CONTRACT = (Path(__file__).parents[3] / "shared/contracts/ws-events.md").read_text(encoding="utf-8")
CLIENT_PART, SERVER_PART = CONTRACT.split("## Server → client")


def examples(section: str) -> list[str]:
    return re.findall(r'`(\{"v":1.*?\})`', section)


def test_contract_examples_were_found():
    assert len(examples(CLIENT_PART)) == 6
    assert len(examples(SERVER_PART)) == 19


@pytest.mark.parametrize("raw", examples(CLIENT_PART))
def test_client_example_round_trips(raw):
    assert client_frame.validate_json(raw).model_dump() == json.loads(raw)


@pytest.mark.parametrize("raw", examples(SERVER_PART))
def test_server_example_round_trips(raw):
    assert server_frame.validate_json(raw).model_dump() == json.loads(raw)


def test_ptt_end_is_accepted():
    assert client_frame.validate_json('{"v":1,"type":"ptt","state":"end"}').state == "end"


@pytest.mark.parametrize(
    "raw",
    [
        '{"v":1,"type":"nope"}',
        '{"v":2,"type":"ping"}',
        '{"v":1,"type":"error","code":"teapot","message":"x"}',
        '{"v":1,"type":"media_request","request_id":"r_1","kind":"audio","target":"x","framing_tip":"y","max_seconds":null}',
    ],
)
def test_frames_outside_the_contract_are_rejected(raw):
    with pytest.raises(ValidationError):
        server_frame.validate_json(raw)
