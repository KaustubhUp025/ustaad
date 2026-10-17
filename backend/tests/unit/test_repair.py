"""start_repair / next_step / confirm_safety basics and the SAFETY.md general-tier rows (except the caption
backstop, T39). The bypass attempts are in test_safety_bypass.py."""

import google.genai
import pytest
from pydantic import ValidationError

from models.fault_card import FaultCard
from models.repair import RepairJob, RepairStep
from models.tools import ConfirmSafetyIn, GateCheck, ProposedStep, StartRepairIn, StepOut
from tools.repair import GENERAL, confirm_safety, next_step, start_repair, step_card

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


def test_a_new_plan_on_the_same_job_starts_from_the_first_step_with_all_gates_open():
    # Power may have been switched back on between plans, so earlier passes do not carry over.
    job = RepairJob(job_id="j_1", gates={"G_MAINS_OFF": "passed", "G_CAP_DISCHARGE": "passed"}, current_step=3)
    _, job = start_repair(StartRepairIn(card_ids=["fc_capacitor"]), job, [card("capacitor")])
    assert job.current_step == 0
    assert job.gates == {"G_MAINS_OFF": "open", "G_CAP_DISCHARGE": "open"}
    out, _ = next_step(job)
    assert out.status == "SAFETY_GATE" and out.gate_id == "G_MAINS_OFF"


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


# Display-only English (language-design.md): each step keeps its words and carries the English beside them.


def test_card_steps_carry_the_cards_english_in_order_and_proposed_steps_their_summary():
    english = card("none", ["Test ek", "Test do"]).model_copy(update={"fix_steps_en": ["Test one", "Test two"]})
    _, job = start_repair(StartRepairIn(card_ids=["fc_none"]), RepairJob(job_id="j_1"), [english])
    assert [(s.instruction, s.instruction_en) for s in job.steps] == [("Test ek", "Test one"), ("Test do", "Test two")]
    _, job = start_repair(general("Test summary"), RepairJob(job_id="j_1"), [])
    assert (job.steps[0].instruction, job.steps[0].instruction_en) == ("Test instruction 1", "Test summary")


def test_a_card_without_english_gives_steps_without_it():
    _, job = start_repair(StartRepairIn(card_ids=["fc_none"]), RepairJob(job_id="j_1"), [card()])
    assert job.steps[0].instruction_en is None


def test_the_english_never_changes_hazard_order_or_gates():
    plain = card("HV", ["Test a", "Test b"])
    english = plain.model_copy(update={"fix_steps_en": ["Test capacitor gas brazing", "Test b"]})
    _, without = start_repair(StartRepairIn(card_ids=["fc_HV"]), RepairJob(job_id="j_1"), [plain])
    _, with_en = start_repair(StartRepairIn(card_ids=["fc_HV"]), RepairJob(job_id="j_1"), [english])
    strip = [s.model_dump(exclude={"instruction_en"}) for s in with_en.steps]
    assert strip == [s.model_dump(exclude={"instruction_en"}) for s in without.steps]
    assert next_step(with_en)[0] == next_step(without)[0]


@pytest.mark.parametrize(
    ("lang", "english", "shown"),
    [("en", "Test one", "Test one"), ("en", None, None), ("hi", "Test one", None), ("te", "Test one", None)],
)
def test_the_step_card_translation_is_the_english_only_in_an_english_session(lang, english, shown):
    step = RepairStep(n=1, instruction="Test ek", instruction_en=english, hazard="none", source=GENERAL)
    card = step_card(StepOut(job_id="j_1", of=1, step=step), lang)
    assert (card.instruction, card.instruction_translated) == ("Test ek", shown)


@pytest.mark.parametrize(
    "summary",
    [
        "Measure the live voltage at the socket",
        "Check at the MCB whether supply is coming",
        "Switch the power on and test the motor",
        "Use a line tester on the terminal",
        "Switch on the MCB and measure the supply voltage",
        "Plug it in and listen to the motor",
    ],
)
def test_a_general_step_that_needs_the_power_on_is_refused_and_never_stored(summary):
    out, job = start_repair(general("Test step at the air filter", summary), RepairJob(job_id="j_1"), [])
    assert out.status == "STOP_REFER" and out.reason == "power_on"
    assert job.steps == []


def test_a_card_step_may_still_need_the_power_on():
    out, job = start_repair(
        StartRepairIn(card_ids=["fc_HV"]), RepairJob(job_id="j_1"), [card("HV", ["Measure the voltage at the socket"])]
    )
    assert out.status == "STARTED" and len(job.steps) == 1


@pytest.mark.parametrize(
    "summary",
    [
        "Check the water supply tap is fully open",
        "Use a continuity tester with the power off to check the fuse",
        "Check the fuse on the board with the power off",
    ],
)
def test_a_general_step_with_the_power_off_is_stored(summary):
    out, job = start_repair(general(summary), RepairJob(job_id="j_1"), [])
    assert out.status == "STARTED" and len(job.steps) == 1
