"""start_repair / next_step / confirm_safety basics and the SAFETY.md general-tier rows (except the caption
backstop, T39). The bypass attempts are in test_safety_bypass.py."""

import google.genai
import pytest
from pydantic import ValidationError

from models.fault_card import FaultCard
from models.repair import RepairJob
from models.tools import ConfirmSafetyIn, GateCheck, ProposedStep, StartRepairIn
from tools.repair import confirm_safety, next_step, start_repair

TELUGU = "కెపాసిటర్ దగ్గర పరీక్ష దశ"  # "test step near the capacitor"


def card(hazard="none", steps=("Test card step",)):
    return FaultCard(
        id=f"fc_{hazard}",
        created_at="2025-05-12T00:00:00Z",
        brand="Voltas",
        error_code="E6",
        symptom="Test symptom",
        fix_steps=list(steps),
        hazard=hazard,
        source={"type": "whatsapp_voice", "author": "Ramesh", "date": "2025-05-12", "audio_uri": "gs://b/n.flac"},
        confidence=0.9,
    )


def general(*summaries):
    steps = [ProposedStep(instruction=f"Test instruction {i}", summary_en=s) for i, s in enumerate(summaries, 1)]
    return StartRepairIn(steps=steps)


def test_proposed_steps_are_stored_as_general_without_any_model_call(monkeypatch):
    def no_client(*args, **kwargs):
        raise AssertionError("start_repair must not call a model")

    monkeypatch.setattr(google.genai, "Client", no_client)
    out, job = start_repair(general("Test step at the air filter", "Test step at the PCB"), RepairJob(job_id="j_1"), [])
    assert out.status == "STARTED" and out.of == 2
    assert [s.source.kind for s in job.steps] == ["general", "general"]
    assert [s.hazard for s in job.steps] == ["none", "HV"]
    assert [s.n for s in job.steps] == [1, 2]


def test_a_telugu_instruction_with_an_english_summary_is_still_tagged():
    _, job = start_repair(
        StartRepairIn(steps=[ProposedStep(instruction=TELUGU, summary_en="Test step at the capacitor")]),
        RepairJob(job_id="j_1"),
        [],
    )
    assert job.steps[0].hazard == "capacitor"
    assert job.steps[0].instruction == TELUGU


def test_the_first_next_step_on_a_general_job_is_the_mains_gate():
    _, job = start_repair(general("Test step at the air filter"), RepairJob(job_id="j_1"), [])
    out, _ = next_step(job)
    assert out.status == "SAFETY_GATE" and out.gate_id == "G_MAINS_OFF"


def test_a_card_job_with_no_hazard_needs_no_gate():
    _, job = start_repair(StartRepairIn(card_ids=["fc_none"]), RepairJob(job_id="j_1"), [card()])
    out, job = next_step(job)
    assert out.status == "STEP" and out.step.instruction == "Test card step"
    assert job.current_step == 1


@pytest.mark.parametrize(
    ("summary", "reason"),
    [
        ("Test step near the magnetron", "microwave_hv"),
        ("Test step at the picture tube", "crt"),
        ("Test step inside the geyser", "geyser_open"),
    ],
)
def test_a_stop_step_returns_stop_refer_and_is_never_stored(summary, reason):
    out, job = start_repair(general("Test step at the air filter", summary), RepairJob(job_id="j_1"), [])
    assert out.status == "STOP_REFER" and out.reason == reason
    assert job.steps == []
    assert summary not in out.model_dump_json()


def test_card_steps_carry_the_card_hazard_and_a_spoken_source():
    out, job = start_repair(
        StartRepairIn(card_ids=["fc_HV"]), RepairJob(job_id="j_1"), [card("HV", ["Test a", "Test b"])]
    )
    assert [s.hazard for s in job.steps] == ["HV", "HV"]
    assert job.steps[0].source.kind == "whatsapp_voice"
    assert job.steps[0].source.label == "Ramesh · May 2025"
    assert job.steps[0].source.audio_uri == "gs://b/n.flac"
    assert [p.n for p in out.steps] == [1, 2]


def test_started_never_carries_instruction_text():
    out, _ = start_repair(StartRepairIn(card_ids=["fc_HV"]), RepairJob(job_id="j_1"), [card("HV", ["Test secret"])])
    assert "Test secret" not in out.model_dump_json()


def test_start_repair_starts_again_from_the_first_step_and_keeps_gates():
    job = RepairJob(job_id="j_1", gates={"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "open"}, current_step=3)
    _, job = start_repair(StartRepairIn(card_ids=["fc_none"]), job, [card()])
    assert job.current_step == 0
    assert job.gates["G_MAINS_OFF"] == "passed"


def test_after_the_last_step_next_step_says_done():
    _, job = start_repair(StartRepairIn(card_ids=["fc_none"]), RepairJob(job_id="j_1"), [card()])
    _, job = next_step(job)
    out, job = next_step(job)
    assert out.status == "DONE" and job.current_step == 1


def test_start_repair_takes_cards_or_steps_not_both_or_neither():
    with pytest.raises(ValidationError):
        StartRepairIn()
    with pytest.raises(ValidationError):
        StartRepairIn(card_ids=["fc_1"], steps=[ProposedStep(instruction="a", summary_en="b")])


def test_a_passed_gate_is_stored_on_the_job():
    out, job = confirm_safety(
        ConfirmSafetyIn(gate_id="G_MAINS_OFF", media_uri="gs://b/r_1.jpg"),
        RepairJob(job_id="j_1"),
        GateCheck(passed=True, reason=None, confidence=0.9),
    )
    assert out.passed and out.reason is None
    assert job.gates == {"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "open"}
