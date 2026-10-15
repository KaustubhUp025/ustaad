import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.inventory import InventoryDelta, InventoryDeltaRequest, InventoryItem, InventoryListResponse

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/inventory.json"


@pytest.fixture
def item():
    return json.loads(FIXTURE.read_text())["items"][0]


def test_synthetic_fixture_round_trip():
    data = json.loads(FIXTURE.read_text())
    response = InventoryListResponse.model_validate_json(FIXTURE.read_text())
    assert response.model_dump(mode="json") == data
    assert response.items[1].category is None
    assert response.items[1].unit_cost_inr is None
    assert InventoryListResponse(items=[]).items == []


@pytest.mark.parametrize("field", [
    "id", "name", "category", "aliases", "qty", "min_qty", "unit_cost_inr", "source", "updated_at",
])
def test_item_fields_required(item, field):
    del item[field]
    with pytest.raises(ValidationError):
        InventoryItem.model_validate(item)


@pytest.mark.parametrize("field", ["qty", "min_qty", "unit_cost_inr"])
@pytest.mark.parametrize("value", [-1, True, False, "2", 2.0, 2.5])
def test_strict_nonnegative_integers(item, field, value):
    item[field] = value
    with pytest.raises(ValidationError):
        InventoryItem.model_validate(item)


@pytest.mark.parametrize("field,value", [
    ("id", "other_1"), ("id", "part_"), ("id", "part_ "),
    ("name", " \t"), ("name", None), ("name", 2), ("category", ""),
    ("category", "\n"), ("aliases", [" "]), ("aliases", [2]),
    ("aliases", None), ("source", "unknown"), ("qty", None), ("min_qty", None),
    ("updated_at", "2026-10-13T12:00:00"),
    ("updated_at", "2026-10-13T12:00:00+05:30"), ("updated_at", "2026-10-13"),
    ("updated_at", 1791892800), ("updated_at", "1791892800"), ("unexpected", "value"),
])
def test_invalid_item(item, field, value):
    with pytest.raises(ValidationError):
        InventoryItem.model_validate({**item, field: value})


@pytest.mark.parametrize("suffix", ["Z", "+00:00"])
def test_utc_serialization(item, suffix):
    item["updated_at"] = "2026-10-13T12:00:00" + suffix
    model = InventoryItem.model_validate(item)
    assert model.model_dump(mode="json")["updated_at"] == "2026-10-13T12:00:00Z"
    assert json.loads(model.model_dump_json())["updated_at"] == "2026-10-13T12:00:00Z"


@pytest.mark.parametrize("source", ["voice", "photo", "manual"])
def test_valid_zero_empty_and_nullable_fields(item, source):
    model = InventoryItem.model_validate({
        **item, "qty": 0, "min_qty": 0, "unit_cost_inr": 0, "aliases": [], "source": source,
    })
    assert model.unit_cost_inr == 0
    nullable = InventoryItem.model_validate({**item, "category": None, "unit_cost_inr": None})
    assert nullable.category is None and nullable.unit_cost_inr is None


@pytest.mark.parametrize("delta", [-2, 2])
def test_signed_deltas(delta):
    request = InventoryDeltaRequest(deltas=[{"part": "synthetic alias", "delta": delta}])
    assert request.deltas[0].delta == delta


@pytest.mark.parametrize("delta", [0, True, False, "2", 2.0, -2.0, 0.5, float("nan"), float("inf")])
def test_rest_deltas_stay_strict(delta):
    with pytest.raises(ValidationError):
        InventoryDelta(part="synthetic part", delta=delta)


@pytest.mark.parametrize("model,data", [
    (InventoryListResponse, {}), (InventoryListResponse, {"items": None}),
    (InventoryListResponse, {"items": [], "extra": 1}),
    (InventoryDeltaRequest, {}), (InventoryDeltaRequest, {"deltas": []}),
    (InventoryDeltaRequest, {"deltas": None}),
    (InventoryDeltaRequest, {"deltas": [{"part": "p", "delta": 1}], "extra": 1}),
    (InventoryDeltaRequest, {"deltas": [{"part": "p", "delta": 1, "extra": 1}]}),
    (InventoryDelta, {"part": "p"}), (InventoryDelta, {"delta": 1}),
    (InventoryDelta, {"part": " \t", "delta": 1}),
    (InventoryDelta, {"part": None, "delta": 1}),
    (InventoryDelta, {"part": "p", "delta": 1, "extra": 1}),
])
def test_required_collections_and_delta_fields(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)
