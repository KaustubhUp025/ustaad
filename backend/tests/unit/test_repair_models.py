import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from models.repair import ApplianceType, GateId, GateState, Hazard, RepairStep, StepSource
from models.ws import StepCard

SCHEMA = json.loads(
    (Path(__file__).parents[3] / "shared/contracts/fault_card.schema.json").read_text(encoding="utf-8")
)["properties"]
SOURCE = {"kind": "general", "label": "General guidance", "audio_uri": None, "doc": None, "page": None}


def test_hazard_and_appliance_type_match_the_fault_card_schema():
    assert set(get_args(Hazard)) == set(SCHEMA["hazard"]["enum"])
    assert set(get_args(ApplianceType)) == set(SCHEMA["appliance_type"]["enum"])


def test_step_source_kinds_are_the_card_sources_plus_manual_photo_and_general():
    kinds = set(get_args(StepSource.model_fields["kind"].annotation))
    assert kinds == set(SCHEMA["source"]["properties"]["type"]["enum"]) | {"manual_photo", "general"}


def test_gate_ids_and_states():
    assert set(get_args(GateId)) == {"G_MAINS_OFF", "G_CAP_DISCHARGE"}
    assert set(get_args(GateState)) == {"open", "passed", "failed"}


def test_a_general_step_is_a_repair_step_and_a_step_card():
    step = RepairStep(n=1, instruction="Plug nikaal ke dikhao", hazard="none", source=StepSource(**SOURCE))
    assert step.model_dump()["source"]["kind"] == "general"
    card = StepCard(job_id="j_1", n=1, of=3, instruction=step.instruction, hazard=step.hazard, source=step.source)
    assert card.source.kind == "general"


@pytest.mark.parametrize(
    "bad",
    [
        {"n": 0},
        {"hazard": "gas"},
        {"source": {**SOURCE, "kind": "web"}},
        {"extra": 1},
    ],
)
def test_repair_step_rejects_bad_values(bad):
    fields = {"n": 1, "instruction": "x", "hazard": "none", "source": SOURCE} | bad
    with pytest.raises(ValidationError):
        RepairStep(**fields)
