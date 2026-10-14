import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from models.fault_card import FaultCardPart, FaultCardSource

SCHEMA = json.loads(
    (Path(__file__).parents[3] / "shared/contracts/fault_card.schema.json").read_text(encoding="utf-8")
)["properties"]


def test_source_types_match_fault_card_schema_independently():
    actual = set(get_args(FaultCardSource.model_fields["type"].annotation))
    expected = set(SCHEMA["source"]["properties"]["type"]["enum"])
    assert actual == expected


def test_source_requires_only_type_and_rejects_unknown_fields():
    source = FaultCardSource(type="synthetic")
    assert source.model_dump(exclude_none=True) == {"type": "synthetic"}

    with pytest.raises(ValidationError):
        FaultCardSource(type="general")
    with pytest.raises(ValidationError):
        FaultCardSource(type="synthetic", label="General guidance")


def test_source_validates_schema_formats_and_strict_page_integer():
    source = FaultCardSource(type="manual", date="2026-10-14", doc="manual.pdf", page=3)
    assert source.model_dump(mode="json", exclude_none=True)["date"] == "2026-10-14"

    for bad in ("2026/10/14", 3.0, True, "3"):
        field = "date" if bad == "2026/10/14" else "page"
        with pytest.raises(ValidationError):
            FaultCardSource.model_validate({"type": "manual", field: bad})


def test_part_requires_name_and_rejects_unknown_fields():
    assert FaultCardPart(name="capacitor").part_no is None
    with pytest.raises(ValidationError):
        FaultCardPart()
    with pytest.raises(ValidationError):
        FaultCardPart(name="capacitor", quantity=1)
