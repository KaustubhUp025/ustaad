"""POST /api/demo/session (rest.md): a token and the seeded demo worker, no login; only demo workers."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.demo_session import worker_store
from app.main import app
from app.session import verify
from models.worker import Worker

FIXTURE = Path(__file__).parents[3] / "seed/fixtures/worker.json"
# The seeded demo worker (seed/fixtures/worker.json), without its id: the document id is the worker id.
DEMO = {k: v for k, v in json.loads(FIXTURE.read_text(encoding="utf-8")).items() if k != "id"}


class Workers:
    def __init__(self, docs):
        self.docs = docs

    def get(self, worker_id):
        data = self.docs.get(worker_id)
        return Worker.model_validate(data | {"id": worker_id}) if data else None


@pytest.fixture
def workers():
    fake = Workers({"w_hi_demo": DEMO, "w_te_demo": DEMO | {"lang": "te"}, "w_real": DEMO | {"demo": False}})
    app.dependency_overrides[worker_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


async def post(json=None):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/demo/session", json=json)


async def test_no_body_gives_the_hindi_demo_worker_and_a_valid_token(workers):
    response = await post()
    assert response.status_code == 200
    body = response.json()
    assert (body["worker"]["id"], body["worker"]["lang"]) == ("w_hi_demo", "hi")
    assert verify(body["token"], datetime.now(UTC)) == "w_hi_demo"
    assert body["ws_url"] == "ws://test/ws/live"


def test_the_seeded_demo_worker_fixture_is_a_valid_worker():
    worker = Worker.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    assert (worker.id, worker.demo) == ("w_hi_demo", True)


async def test_another_demo_worker_can_be_asked_for(workers):
    assert (await post({"worker_id": "w_te_demo"})).json()["worker"]["lang"] == "te"


@pytest.mark.parametrize("worker_id", ["w_real", "w_missing"])
async def test_a_worker_that_is_not_a_demo_worker_gets_not_found(workers, worker_id):
    response = await post({"worker_id": worker_id})
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")


# Onboarding (T21, G1): each visitor gets a new, empty demo worker, so two judges never share one interview.


class CreatingWorkers(Workers):
    def create(self, worker):
        self.docs[worker.id] = worker.model_dump(mode="json", exclude={"id"})


async def test_onboarding_gives_each_visitor_a_new_empty_demo_worker_in_his_language():
    fake = CreatingWorkers({})
    app.dependency_overrides[worker_store] = lambda: fake
    try:
        first, second = (await post({"onboarding": True, "lang": "te"})).json(), (await post({"onboarding": True})).json()
    finally:
        app.dependency_overrides.clear()
    assert first["worker"]["id"].startswith("w_onb_") and first["worker"]["id"] != second["worker"]["id"]
    assert (first["worker"]["lang"], second["worker"]["lang"]) == ("te", "hi")
    assert (first["worker"]["trades"], first["worker"]["onboarding_done"], first["worker"]["demo"]) == ([], False, True)
    assert verify(first["token"], datetime.now(UTC)) == first["worker"]["id"]
    assert set(fake.docs) == {first["worker"]["id"], second["worker"]["id"]}
