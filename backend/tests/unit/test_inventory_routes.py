import json
import socket
from pathlib import Path

import google.auth
import httpx
import pytest
from google.cloud import firestore, storage

from app.main import app
from models.inventory import InventoryListResponse

ROOT = Path(__file__).parents[3]


@pytest.fixture(autouse=True)
def forbid_external_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("inventory fixture route must stay offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(google.auth, "default", forbidden)
    monkeypatch.setattr(firestore, "Client", forbidden)
    monkeypatch.setattr(firestore, "AsyncClient", forbidden)
    monkeypatch.setattr(storage, "Client", forbidden)


async def test_inventory_replays_fixture_through_response_model():
    fixture = json.loads((ROOT / "seed/fixtures/inventory.json").read_text())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/inventory")

    assert response.status_code == 200
    assert response.json() == fixture
    validated = InventoryListResponse.model_validate(response.json())
    assert validated.model_dump(mode="json") == fixture
    assert [item["qty"] for item in response.json()["items"]] == [5, 0]
    assert response.json()["items"][1]["category"] is None
    assert response.json()["items"][1]["unit_cost_inr"] is None
    assert all(item["updated_at"] == "2026-10-13T12:00:00Z" for item in response.json()["items"])


async def test_inventory_does_not_register_patch_and_preserves_error_envelope():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/api/inventory", json={"deltas": []})

    assert response.status_code == 405
    assert response.json() == {"error": {"code": "http_error", "message": "Request failed"}}
