"""Dashboard REST routes (T24), exercised only with injected in-memory stores."""

import socket
from datetime import UTC, datetime

import google.auth
import httpx
import pytest
from google.cloud import firestore, storage

from app import session
from app.dashboard import dashboard_store
from app.fault_cards import card_store
from app.imports import import_store
from app.main import app
from models.dashboard import DashboardSummary
from models.fault_card import FaultCard
from models.imports import Import

NOW = datetime(2026, 10, 18, tzinfo=UTC)


@pytest.fixture(autouse=True)
def forbid_external_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dashboard route tests must stay offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(google.auth, "default", forbidden)
    monkeypatch.setattr(firestore, "Client", forbidden)
    monkeypatch.setattr(firestore, "AsyncClient", forbidden)
    monkeypatch.setattr(storage, "Client", forbidden)


def fault_card(card_id: str, *, appliance_type: str, review_status: str, brand: str, code: str) -> FaultCard:
    return FaultCard.model_validate(
        {
            "id": card_id,
            "created_at": NOW,
            "brand": brand,
            "error_code": code,
            "symptom": "Synthetic symptom",
            "fix_steps": ["Synthetic step"],
            "hazard": "none",
            "source": {"type": "synthetic"},
            "confidence": 0.9,
            "appliance_type": appliance_type,
            "review_status": review_status,
        }
    )


def import_record(import_id: str, worker_id: str) -> Import:
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
            "started_at": NOW,
            "finished_at": None,
        }
    )


class FakeCards:
    def __init__(self):
        self.cards = [
            fault_card("fc_ac", appliance_type="split_ac", review_status="needs_review", brand="Voltas", code="E6"),
            fault_card("fc_washer", appliance_type="washing_machine", review_status="approved", brand="LG", code="OE"),
        ]

    def list(self):
        return self.cards


class FakeImports:
    def __init__(self):
        self.records = {"i_own": import_record("i_own", "w_hi_demo"), "i_other": import_record("i_other", "w_te_demo")}

    def get(self, import_id):
        return self.records.get(import_id)


class FakeDashboard:
    def summary(self, worker_id, now):
        assert (worker_id, now.tzinfo) == ("w_hi_demo", UTC)
        return DashboardSummary(cards=8, cards_needing_review=2, jobs_7d=3, imports=1)


@pytest.fixture
def world():
    app.dependency_overrides.update(
        {card_store: FakeCards, import_store: FakeImports, dashboard_store: FakeDashboard}
    )
    yield
    app.dependency_overrides.clear()


async def call(path, worker_id="w_hi_demo"):
    headers = {"Authorization": f"Bearer {session.issue(worker_id, datetime.now(UTC))}"} if worker_id else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers=headers)


async def test_fault_cards_apply_the_documented_filters(world):
    response = await call("/api/fault-cards?q=voltas&brand=Voltas&code=E6&status=needs_review&appliance_type=split_ac")

    assert response.status_code == 200
    assert ([card["id"] for card in response.json()["items"]], response.json()["next"]) == (["fc_ac"], None)


async def test_fault_cards_reject_an_unknown_appliance_type_with_the_shared_envelope(world):
    response = await call("/api/fault-cards?appliance_type=not_an_appliance")

    assert (response.status_code, response.json()["error"]["code"]) == (422, "validation_error")


async def test_import_is_visible_only_to_its_worker_and_missing_records_are_safe_404s(world):
    own = await call("/api/imports/i_own")
    other = await call("/api/imports/i_other")
    missing = await call("/api/imports/i_missing")

    assert (own.status_code, own.json()["id"], own.json()["status"]) == (200, "i_own", "extracting")
    assert [(response.status_code, response.json()["error"]["code"]) for response in (other, missing)] == [
        (404, "not_found"),
        (404, "not_found"),
    ]


async def test_dashboard_summary_uses_the_documented_shape(world):
    response = await call("/api/dashboard/summary")

    assert response.json() == {"cards": 8, "cards_needing_review": 2, "jobs_7d": 3, "imports": 1}


@pytest.mark.parametrize("path", ["/api/fault-cards", "/api/imports/i_own", "/api/dashboard/summary"])
async def test_dashboard_routes_require_a_session(world, path):
    response = await call(path, worker_id=None)

    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthorized")
