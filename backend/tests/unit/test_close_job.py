"""close_job (T22, G4): a finished job becomes a closed job and a job card for review, and the parts he used come
off his stock. Pure tool; the agent wrapper saves the card and changes the stock."""

import json
from datetime import UTC, datetime
from pathlib import Path

from models.repair import RepairJob
from models.tools import AlreadyClosed, Closed, CloseJobIn, SafetyGateOut
from tools.close_job import close_job, stock_deltas

FIXTURE = json.loads((Path(__file__).parents[3] / "seed/fixtures/close_job.json").read_text())
NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


def job(**changes) -> RepairJob:
    return RepairJob.model_validate(FIXTURE["job"] | changes)


def answers(**changes) -> CloseJobIn:
    return CloseJobIn.model_validate(FIXTURE["close"] | changes)


def test_closing_drafts_a_job_card_for_review_with_the_jobs_photo():
    out, _, card = close_job(answers(), job(), "fc_job1", NOW)
    assert out == Closed(card_id="fc_job1")
    assert (card.id, card.brand, card.error_code, card.appliance_type) == ("fc_job1", "LG", "", "split_ac")
    assert (card.symptom, card.root_cause, card.fix_steps) == (
        "Test symptom said by the worker",
        "Test cause said by the worker",
        ["Test fix said by the worker"],
    )
    assert [p.name for p in card.parts] == ["capacitor"]
    # The last photo Ustaad asked for and read; a gate photo (no findings) is not the job's photo.
    assert card.photo_uri == "gs://media/jobs/j_g4/r_part/b.jpg"
    assert (card.source.type, card.source.date) == ("job", NOW.date())
    assert card.review_status == "needs_review"


def test_a_job_with_only_a_gate_photo_and_no_type_still_closes():
    # Phone test (Oct 17): photo_uri=None reached the strict card model and the crash ended the Live session.
    _, _, card = close_job(answers(appliance_type=None, brand=None), job(media=FIXTURE["job"]["media"][:1]), "fc_1", NOW)
    assert (card.photo_uri, card.appliance_type, card.brand) == (None, None, "")


def test_the_card_hazard_is_never_below_the_jobs_steps():
    _, _, card = close_job(answers(), job(), "fc_job1", NOW)
    assert card.hazard == "capacitor"


def test_the_job_is_closed_with_the_outcome_and_parts():
    _, closed, _ = close_job(answers(), job(), "fc_job1", NOW)
    assert (closed.status, closed.outcome, closed.closed_at) == ("closed", "Test cause said by the worker", NOW)
    assert [(p.part, p.qty) for p in closed.parts_used] == [("capacitor", 1)]


def test_a_job_with_an_open_gate_is_not_closed():
    gated = job(gates={"G_MAINS_OFF": "open", "G_CAP_DISCHARGE": "open"}, current_step=0)
    out, after, card = close_job(answers(), gated, "fc_job1", NOW)
    assert isinstance(out, SafetyGateOut) and out.gate_id == "G_MAINS_OFF"
    assert (after, card) == (gated, None)


def test_a_second_close_changes_nothing():
    _, closed, _ = close_job(answers(), job(), "fc_job1", NOW)
    out, again, card = close_job(answers(), closed, "fc_job2", NOW)
    assert (out, again, card) == (AlreadyClosed(), closed, None)


def test_each_part_used_comes_off_the_stock():
    assert [(d.part, d.delta) for d in stock_deltas(answers().parts_used)] == [("capacitor", -1)]
