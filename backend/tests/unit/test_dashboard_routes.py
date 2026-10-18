"""Offline dependency-injected coverage for the dashboard route functions."""

from datetime import UTC, datetime

import httpx
import pytest
from fastapi import HTTPException

from app import session
from app.fault_cards import list_fault_cards
from app.imports import get_import, import_store, list_imports
from app.main import app
from app.session import require_session
from models.fault_card import FaultCard
from models.imports import Import

NOW = datetime(2026, 10, 18, tzinfo=UTC)


def fault_card(
    card_id: str, *, appliance_type: str, review_status: str, brand: str, code: str, symptom: str
) -> FaultCard:
    return FaultCard.model_validate(
        {
            "id": card_id,
            "created_at": NOW,
            "brand": brand,
            "error_code": code,
            "symptom": symptom,
            "fix_steps": ["Synthetic step"],
            "hazard": "none",
            "source": {"type": "synthetic"},
            "confidence": 0.9,
            "appliance_type": appliance_type,
            "review_status": review_status,
        }
    )


def import_record(import_id: str, worker_id: str, started_at: datetime = NOW) -> Import:
    return Import.model_validate(
        {
            "id": import_id,
            "worker_id": worker_id,
            "group_name": "Synthetic group",
            "status": "extracting",
            "files_total": 3,
            "audio_total": 2,
            "audio_done": 1,
            "threads": 1,
            "cards_created": 1,
            "cards_needing_review": 0,
            "errors": [],
            "started_at": started_at,
            "finished_at": None,
        }
    )


class FakeCards:
    def __init__(self):
        self.cards = [
            fault_card(
                "fc_ac",
                appliance_type="split_ac",
                review_status="needs_review",
                brand="Voltas",
                code="E6",
                symptom="Indoor unit does not communicate",
            ),
            fault_card(
                "fc_washer",
                appliance_type="washing_machine",
                review_status="approved",
                brand="LG",
                code="OE",
                symptom="Drain pump is blocked",
            ),
        ]

    def list(self):
        return self.cards


class FakeImports:
    def __init__(self):
        self.records = {
            "i_own_old": import_record("i_own_old", "w_hi_demo", NOW.replace(day=17)),
            "i_own_new": import_record("i_own_new", "w_hi_demo"),
            "i_other": import_record("i_other", "w_te_demo"),
        }

    def get(self, import_id):
        return self.records.get(import_id)

    def list(self, worker_id):
        return sorted(
            (record for record in self.records.values() if record.worker_id == worker_id),
            key=lambda record: record.started_at,
            reverse=True,
        )[:20]


@pytest.mark.parametrize(
    ("query", "expected"),
    [("blocked", ["fc_washer"]), (None, ["fc_ac", "fc_washer"])],
)
def test_fault_card_query_matches_a_symptom_even_when_other_fields_do_not(query, expected):
    response = list_fault_cards(FakeCards(), "w_hi_demo", q=query)

    assert [card.id for card in response.items] == expected
    assert all("embedding" not in card.model_dump() for card in response.items)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"brand": "LG"}, ["fc_washer"]),
        ({"code": "E6"}, ["fc_ac"]),
        ({"status": "needs_review"}, ["fc_ac"]),
        ({"appliance_type": "split_ac"}, ["fc_ac"]),
    ],
)
def test_fault_cards_apply_each_non_query_filter_independently(kwargs, expected):
    response = list_fault_cards(FakeCards(), "w_hi_demo", **kwargs)

    assert [card.id for card in response.items] == expected


def test_import_list_is_worker_scoped_and_newest_first():
    response = list_imports(FakeImports(), "w_hi_demo")

    assert [item.id for item in response.items] == ["i_own_new", "i_own_old"]


def test_import_detail_is_visible_only_to_its_worker_and_missing_records_are_safe_404s():
    store = FakeImports()

    assert get_import("i_own_new", store, "w_hi_demo").id == "i_own_new"
    for import_id in ("i_other", "i_missing"):
        with pytest.raises(HTTPException) as raised:
            get_import(import_id, store, "w_hi_demo")
        assert raised.value.status_code == 404


def test_import_list_requires_a_session_dependency():
    with pytest.raises(HTTPException) as raised:
        require_session(None)

    assert raised.value.status_code == 401


async def test_import_list_http_route_requires_auth_and_keeps_workers_isolated_in_newest_order():
    app.dependency_overrides[import_store] = FakeImports
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            missing = await client.get("/api/imports")
            token = session.issue("w_hi_demo", datetime.now(UTC))
            own = await client.get("/api/imports", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 401
    assert [item["id"] for item in own.json()["items"]] == ["i_own_new", "i_own_old"]
