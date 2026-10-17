"""The Live session's starting state (T21): who he is, where he works, and whether the onboarding interview is due."""

import json
from pathlib import Path

from app.ws_live import session_state
from models.worker import Worker
from tests.unit.test_profile import NOW
from tools.profile import fresh_worker

DEMO = Worker.model_validate(json.loads((Path(__file__).parents[3] / "seed/fixtures/worker.json").read_text()))


def test_an_onboarded_worker_gets_his_name_area_and_no_interview():
    state = session_state(DEMO, "hi", "j_1")
    assert state == {
        "language_name": "Hindi, written in Devanagari script", "lang": "hi", "job_id": "j_1", "worker_id": "w_hi_demo",
        "worker_name": "Raju (demo)", "area": "pincode 201301", "onboarding": "done",
    }


def test_a_new_worker_gets_the_interview_in_his_language():
    state = session_state(fresh_worker("w_onb_1", "te", NOW), "te", "j_1")
    assert (state["onboarding"], state["worker_id"], state["language_name"]) == (
        "pending", "w_onb_1", "Telugu, written in Telugu script")
    assert "worker_name" not in state and "area" not in state
