"""GET /api/quotes/{qrid} and POST /api/quotes/{qid}/approve (rest.md) against an in-memory store and a fake bot:
ranked quotes for this worker only, and approval confirms the quote and messages that vendor."""

from datetime import UTC, datetime

import httpx
import pytest

from app import session
from app.main import app
from app.quotes import quote_store
from clients.telegram import telegram_bot
from models.quotes import ParsedReply, QuotesResponse
from tests.unit.fake_quotes import FakeBot, FakeQuoteStore, sent_request
from tools import quotes


def reply(price, eta_minutes):
    return ParsedReply(
        price_inr=price, available=True, eta=f"{eta_minutes} min", eta_minutes=eta_minutes, confidence=0.9
    )


@pytest.fixture
def world():
    store, bot = FakeQuoteStore(), FakeBot()
    now = datetime.now(UTC)
    request, (a, b, c) = sent_request(now=now)
    a = quotes.parsed(quotes.replied(a, "300", False, now), reply(300, 60), now)
    c = quotes.parsed(quotes.replied(c, "250", True, now), reply(250, 120), now)
    store.create(request, [a, b, c])
    app.dependency_overrides.update({quote_store: lambda: store, telegram_bot: lambda: bot})
    yield store, bot, request.id, {"a": a.id, "b": b.id, "c": c.id}
    app.dependency_overrides.clear()


async def call(method, path, worker_id="w_hi_demo"):
    headers = {"Authorization": f"Bearer {session.issue(worker_id, datetime.now(UTC))}"} if worker_id else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, headers=headers)


async def test_get_returns_the_request_and_its_quotes_ranked(world):
    _, _, qrid, ids = world
    response = await call("GET", f"/api/quotes/{qrid}")
    assert response.status_code == 200
    body = QuotesResponse.model_validate(response.json())
    assert [q.id for q in body.quotes] == [ids["c"], ids["a"], ids["b"]]
    assert "tg_chat_id" not in response.json()["quotes"][0]


@pytest.mark.parametrize(
    ("path", "worker_id", "status"),
    [
        ("/api/quotes/qr_1", None, 401),
        ("/api/quotes/qr_1", "w_te_demo", 404),
        ("/api/quotes/qr_none", "w_hi_demo", 404),
    ],
)
async def test_get_needs_the_workers_own_request(world, path, worker_id, status):
    assert (await call("GET", path, worker_id)).status_code == status


async def test_approve_confirms_and_messages_that_vendor(world):
    _, bot, _, ids = world
    response = await call("POST", f"/api/quotes/{ids['c']}/approve")
    assert response.status_code == 200
    body = QuotesResponse.model_validate(response.json())
    assert (body.request.status, body.request.approved_quote_id) == ("approved", ids["c"])
    assert next(q for q in body.quotes if q.id == ids["c"]).state == "CONFIRMED"
    assert bot.sent == [
        (1003, "Ustaad order #qr_1 confirmed\noutdoor PCB x 1 at Rs 250 per piece\nDelivery: 120 min", [])
    ]


async def test_approve_twice_or_an_unquoted_vendor_is_409(world):
    _, bot, _, ids = world
    assert (await call("POST", f"/api/quotes/{ids['b']}/approve")).status_code == 409
    assert (await call("POST", f"/api/quotes/{ids['c']}/approve")).status_code == 200
    assert (await call("POST", f"/api/quotes/{ids['a']}/approve")).status_code == 409
    assert len(bot.sent) == 1


@pytest.mark.parametrize(("qid", "worker_id"), [("q_none", "w_hi_demo"), (None, "w_te_demo")])
async def test_approve_someone_elses_or_a_missing_quote_is_404(world, qid, worker_id):
    _, bot, _, ids = world
    assert (await call("POST", f"/api/quotes/{qid or ids['c']}/approve", worker_id)).status_code == 404
    assert bot.sent == []
