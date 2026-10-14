import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from models.fault_card import FaultCard, FaultCardPart, FaultCardSource, ReviewStatus
from models.repair import ApplianceType, Hazard

CONTRACT = json.loads(
    (Path(__file__).parents[3] / "shared/contracts/fault_card.schema.json").read_text(encoding="utf-8")
)
SCHEMA = CONTRACT["properties"]
SOURCE_SCHEMA = SCHEMA["source"]
PART_SCHEMA = SCHEMA["parts"]["items"]
FIXTURE = Path(__file__).parents[3] / "seed/fixtures/fault_cards.json"
REQUIRED = set(CONTRACT["required"])


def fixture_card():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))[0]


def test_model_property_names_match_contract_exactly():
    assert set(FaultCard.model_fields) == set(SCHEMA)
    assert set(FaultCardSource.model_fields) == set(SOURCE_SCHEMA["properties"])
    assert set(FaultCardPart.model_fields) == set(PART_SCHEMA["properties"])


def test_model_required_fields_match_contract_exactly():
    assert {name for name, field in FaultCard.model_fields.items() if field.is_required()} == REQUIRED
    assert {name for name, field in FaultCardSource.model_fields.items() if field.is_required()} == set(
        SOURCE_SCHEMA["required"]
    )
    assert {name for name, field in FaultCardPart.model_fields.items() if field.is_required()} == set(
        PART_SCHEMA["required"]
    )


def test_enums_match_fault_card_schema():
    actual = set(get_args(FaultCardSource.model_fields["type"].annotation))
    expected = set(SOURCE_SCHEMA["properties"]["type"]["enum"])
    assert actual == expected
    assert set(get_args(Hazard)) == set(SCHEMA["hazard"]["enum"])
    assert set(get_args(ApplianceType)) == set(SCHEMA["appliance_type"]["enum"])
    assert set(get_args(ReviewStatus)) == set(SCHEMA["review_status"]["enum"])


def test_source_requires_only_type_and_rejects_unknown_fields():
    source = FaultCardSource(type="synthetic")
    assert source.model_dump(exclude_none=True) == {"type": "synthetic"}

    with pytest.raises(ValidationError):
        FaultCardSource(type="general")
    with pytest.raises(ValidationError):
        FaultCardSource(type="synthetic", label="General guidance")


def test_source_date_and_page_serialize_to_contract_formats():
    source = FaultCardSource(type="manual", date="2026-10-14", doc="manual.pdf", page=3)
    assert source.model_dump(mode="json", exclude_unset=True, exclude_none=True)["date"] == "2026-10-14"

    for bad in (3.0, True, "3"):
        with pytest.raises(ValidationError):
            FaultCardSource.model_validate({"type": "manual", "page": bad})


@pytest.mark.parametrize(
    "bad_date",
    [0, 86400, 0.0, True, "2026/10/14", "20261014", "2026-10-14T00:00:00Z", "2026-02-30"],
)
def test_source_date_accepts_only_yyyy_mm_dd_strings(bad_date):
    with pytest.raises(ValidationError):
        FaultCardSource.model_validate({"type": "manual", "date": bad_date})


def test_part_requires_name_and_preserves_schema_allowed_extra_fields():
    assert FaultCardPart(name="capacitor").part_no is None
    with pytest.raises(ValidationError):
        FaultCardPart()
    part = FaultCardPart.model_validate({"name": "Model validation fixture part", "future_field": "preserved"})
    assert part.model_dump() == {"name": "Model validation fixture part", "part_no": None, "future_field": "preserved"}


def test_fixture_validates_and_public_serialization_round_trips():
    data = fixture_card()
    card = FaultCard.model_validate(data)
    assert card.to_public_dict() == data
    assert "embedding" not in card.to_public_dict()


@pytest.mark.parametrize("field", sorted(REQUIRED))
def test_fault_card_required_fields(field):
    data = fixture_card()
    del data[field]
    with pytest.raises(ValidationError):
        FaultCard.model_validate(data)


def test_optional_fields_may_be_omitted_but_not_null():
    data = {key: value for key, value in fixture_card().items() if key in REQUIRED}
    card = FaultCard.model_validate(data)
    public = card.to_public_dict()
    assert set(public) == REQUIRED
    assert all(value is not None for value in public.values())
    assert all(value is not None for value in public["source"].values())

    optional = set(SCHEMA) - REQUIRED
    for field in optional:
        with pytest.raises(ValidationError):
            FaultCard.model_validate(data | {field: None})


def test_public_serialization_keeps_populated_optional_and_part_extra_fields():
    data = fixture_card() | {
        "worker_id": "w_model_validation",
        "model": "Model validation fixture; contains no repair guidance",
        "parts": [{"name": "Model validation fixture part", "future_field": "preserved"}],
        "source": {"type": "synthetic", "date": "2026-10-14", "doc": "model-validation-fixture"},
    }
    public = FaultCard.model_validate(data).to_public_dict()
    assert public["worker_id"] == data["worker_id"]
    assert public["model"] == data["model"]
    assert public["source"] == data["source"]
    assert public["parts"] == data["parts"]


@pytest.mark.parametrize(
    "change",
    [
        {"id": "card_1"},
        {"fix_steps": []},
        {"confidence": -0.01},
        {"confidence": 1.01},
        {"confidence": True},
        {"verified_count": -1},
        {"verified_count": 1.0},
        {"created_at": "2026-10-14T12:00:00"},
        {"created_at": "2026-10-14T17:30:00+05:30"},
        {"appliance_type": "ac"},
        {"hazard": "high"},
        {"review_status": "pending"},
        {"embedding": [0.0] * 768},
    ],
)
def test_fault_card_constraints_and_private_fields(change):
    with pytest.raises(ValidationError):
        FaultCard.model_validate(fixture_card() | change)


@pytest.mark.parametrize("confidence", [0, 1])
def test_confidence_endpoints_are_valid(confidence):
    assert FaultCard.model_validate(fixture_card() | {"confidence": confidence}).confidence == confidence


@pytest.mark.parametrize("source_type", SOURCE_SCHEMA["properties"]["type"]["enum"])
def test_all_fault_card_source_variants(source_type):
    data = fixture_card()
    data["source"] = {"type": source_type}
    assert FaultCard.model_validate(data).source.type == source_type


def test_optional_nested_properties_reject_null():
    with pytest.raises(ValidationError):
        FaultCardSource(type="manual", doc=None)
    with pytest.raises(ValidationError):
        FaultCardPart(name="capacitor", part_no=None)


def test_utc_timestamps_serialize_as_z():
    data = fixture_card()
    data["created_at"] = "2026-10-14T12:00:00+00:00"
    card = FaultCard.model_validate(data)
    assert card.to_public_dict()["created_at"] == "2026-10-14T12:00:00Z"
