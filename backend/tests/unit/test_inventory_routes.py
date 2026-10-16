"""GET / PATCH /api/inventory (rest.md, BUILD-GUIDE T18) against an in-memory store: still offline. Replaces the T10
fixture-only tests (GET replayed inventory.json; PATCH was not registered), as T18 adds the store and PATCH."""

import socket

import google.auth
import httpx
import pytest
from google.cloud import firestore, storage

from app.inventory import inventory_store
from app.main import app
from models.inventory import InventoryListResponse
from tests.unit.fake_inventory import FakeInventoryStore, stock


@pytest.fixture(autouse=True)
def forbid_external_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("inventory route tests must stay offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(google.auth, "default", forbidden)
    monkeypatch.setattr(firestore, "Client", forbidden)
    monkeypatch.setattr(firestore, "AsyncClient", forbidden)
    monkeypatch.setattr(storage, "Client", forbidden)


@pytest.fixture
def store():
    fake = FakeInventoryStore(stock())
    app.dependency_overrides[inventory_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


async def call(method, json=None):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, "/api/inventory", json=json)


async def test_get_lists_the_workers_stock_through_the_response_model(store):
    response = await call("GET")
    assert response.status_code == 200
    items = InventoryListResponse.model_validate(response.json()).items
    assert [(i.id, i.qty) for i in items] == [("part_cap25", 5), ("part_pcb", 0), ("part_tape", 10)]


async def test_patch_applies_the_deltas_and_returns_the_list(store):
    response = await call("PATCH", {"deltas": [{"part": "capacitor 2.5uF", "delta": -2}]})
    assert response.status_code == 200
    cap = next(i for i in response.json()["items"] if i["id"] == "part_cap25")
    assert (cap["qty"], cap["source"]) == (3, "manual")


@pytest.mark.parametrize(
    ("deltas", "status", "code"),
    [
        ([{"part": "compressor", "delta": 1}], 404, "not_found"),
        ([{"part": "Outdoor PCB", "delta": -1}], 409, "conflict"),
        ([{"part": "capacitor", "delta": -1}, {"part": "compressor", "delta": 1}], 404, "not_found"),
    ],
)
async def test_a_failed_patch_changes_nothing_and_keeps_the_error_envelope(store, deltas, status, code):
    response = await call("PATCH", {"deltas": deltas})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert store.by_worker["w_hi_demo"]["part_cap25"].qty == 5


async def test_an_empty_patch_is_a_validation_error(store):
    response = await call("PATCH", {"deltas": []})
    assert (response.status_code, response.json()["error"]["code"]) == (422, "validation_error")
