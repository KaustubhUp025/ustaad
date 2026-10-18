"""The Live quote tools: requests go to saved vendors and get_quotes reports only this worker's job safely."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk
from agent.quote_tools import quote_tools
from models.quotes import ParsedReply
from tests.unit.fake_quotes import FakeBot, FakeQuoteStore, sent_request
from tools import quotes


class Desk(MediaDesk):
    def __init__(self) -> None:
        super().__init__("j_1", "bucket")
        self.shown = []

    async def show(self, frame) -> None:
        self.shown.append(frame)


def setup(bot=None):
    store, bot, desk = FakeQuoteStore(), bot or FakeBot(), Desk()
    request, updates = quote_tools(store, bot, desk)
    return store, bot, desk, request, updates, SimpleNamespace(state={"worker_id": "w_hi_demo", "job_id": "j_1"})


def test_request_quotes_is_non_blocking_and_answers_when_idle():
    *_, request, _updates, _ = setup()
    assert (request.name, request.behavior) == ("request_quotes", types.Behavior.NON_BLOCKING)
    assert request.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


def test_get_quotes_is_blocking_and_returns_when_idle():
    *_, updates, _ = setup()
    assert (updates.name, updates.behavior) == ("get_quotes", types.Behavior.BLOCKING)
    assert updates.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


async def test_pcb_nahi_hai_sends_the_request_to_every_saved_vendor():
    store, bot, desk, request_tool, _, ctx = setup()
    out = await request_tool.run_async(
        args={"part": "outdoor PCB", "specs": "Daikin FTKF50", "qty": 1}, tool_context=ctx
    )
    qrid = out["quote_request_id"]
    assert out["vendors"] == ["Vendor A", "Vendor B", "Vendor C"]
    request, docs = store.get(qrid)
    assert (request.job_id, request.worker_id, request.part, request.specs, request.qty) == (
        "j_1",
        "w_hi_demo",
        "outdoor PCB",
        "Daikin FTKF50",
        1,
    )
    assert [chat for chat, _, _ in bot.sent] == [1001, 1002, 1003]
    _, text, buttons = bot.sent[0]
    assert text.startswith(f"Ustaad stock request #{qrid}\noutdoor PCB x 1\n")
    assert [b.data for b in buttons] == [f"avail:{docs[0].id}", f"na:{docs[0].id}"]
    assert [(q.state, q.tg_message_id) for q in docs] == [("SENT", 901), ("SENT", 902), ("SENT", 903)]
    (frame,) = desk.shown
    assert (frame.type, frame.quote_request_id, [i.vendor for i in frame.items]) == (
        "quotes",
        qrid,
        ["Vendor A", "Vendor B", "Vendor C"],
    )


async def test_a_vendor_who_cannot_be_reached_is_left_out():
    class BlockedB(FakeBot):
        async def send_message(self, chat_id, text, buttons=()):
            if chat_id == 1002:
                raise RuntimeError("Telegram sendMessage failed: 403 Forbidden: bot was blocked by the user")
            return await super().send_message(chat_id, text, buttons)

    store, _, _, request_tool, _, ctx = setup(BlockedB())
    out = await request_tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out["vendors"] == ["Vendor A", "Vendor C"]
    _, docs = store.get(out["quote_request_id"])
    assert [q.state for q in docs] == ["SENT", "CREATED", "SENT"]


async def test_no_saved_vendors():
    store, bot, desk, request_tool, _, ctx = setup()
    store.vendor_list = []
    out = await request_tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out == {"quote_request_id": None, "vendors": []}
    assert (store.requests, bot.sent, desk.shown) == ({}, [], [])


def quoted(quote, price: int, eta_minutes: int, from_voice: bool = False):
    now = datetime.now(UTC)
    reply = ParsedReply(
        price_inr=price, available=True, eta=f"{eta_minutes} min", eta_minutes=eta_minutes, confidence=0.9
    )
    return quotes.parsed(quotes.replied(quote, "", from_voice, now), reply, now)


async def test_get_quotes_reports_a_quoted_vendor_without_server_only_fields():
    store, _, _, _, updates, ctx = setup()
    request, (a, b, c) = sent_request(now=datetime.now(UTC))
    store.create(request, [quoted(a, 300, 60, from_voice=True), b, c])

    out = await updates.run_async(args={}, tool_context=ctx)

    assert out == {
        "requests": [
            {
                "part": "outdoor PCB",
                "qty": 1,
                "status": "open",
                "quotes": [
                    {"vendor_name": "Vendor A", "state": "QUOTED", "available": True, "price_inr": 300, "eta": "60 min", "from_voice": True},
                    {"vendor_name": "Vendor B", "state": "SENT", "available": None, "price_inr": None, "eta": None, "from_voice": False},
                    {"vendor_name": "Vendor C", "state": "SENT", "available": None, "price_inr": None, "eta": None, "from_voice": False},
                ],
            }
        ]
    }


async def test_get_quotes_keeps_no_reply_vendors_waiting():
    store, _, _, _, updates, ctx = setup()
    request, docs = sent_request(now=datetime.now(UTC))
    store.create(request, docs)

    out = await updates.run_async(args={}, tool_context=ctx)

    assert [row["available"] for row in out["requests"][0]["quotes"]] == [None, None, None]
    assert [row["price_inr"] for row in out["requests"][0]["quotes"]] == [None, None, None]


async def test_get_quotes_lists_newest_requests_first():
    store, _, _, _, updates, ctx = setup()
    now = datetime.now(UTC)
    older, older_docs = sent_request(qrid="qr_old", now=now - timedelta(minutes=1))
    newer, newer_docs = sent_request(qrid="qr_new", now=now)
    older = older.model_copy(update={"part": "older part"})
    newer = newer.model_copy(update={"part": "newer part"})
    store.create(older, older_docs)
    store.create(newer, newer_docs)

    out = await updates.run_async(args={}, tool_context=ctx)

    assert [request["part"] for request in out["requests"]] == ["newer part", "older part"]
    assert [request["qty"] for request in out["requests"]] == [1, 1]
    assert [request["quotes"][0]["state"] for request in out["requests"]] == ["SENT", "SENT"]


async def test_get_quotes_reports_expired_request_and_unanswered_quotes():
    store, _, _, _, updates, ctx = setup()
    request, docs = sent_request(now=datetime.now(UTC) - timedelta(minutes=31))
    store.create(request, docs)

    out = await updates.run_async(args={}, tool_context=ctx)

    assert out["requests"][0]["status"] == "expired"
    assert [quote["state"] for quote in out["requests"][0]["quotes"]] == ["EXPIRED", "EXPIRED", "EXPIRED"]


async def test_get_quotes_preserves_existing_quote_ranking():
    store, _, _, _, updates, ctx = setup()
    request, (a, b, c) = sent_request(now=datetime.now(UTC))
    store.create(request, [quoted(a, 300, 60), b, quoted(c, 250, 120)])

    out = await updates.run_async(args={}, tool_context=ctx)

    assert [row["vendor_name"] for row in out["requests"][0]["quotes"]] == ["Vendor C", "Vendor A", "Vendor B"]


async def test_get_quotes_never_reads_another_worker_or_job():
    store, _, _, _, updates, ctx = setup()
    now = datetime.now(UTC)
    other_worker, other_worker_docs = quotes.new_request("qr_other_worker", "j_1", "w_te_demo", "part", "", 1, [], now)
    other_job, other_job_docs = quotes.new_request("qr_other_job", "j_other", "w_hi_demo", "part", "", 1, [], now)
    store.create(other_worker, other_worker_docs)
    store.create(other_job, other_job_docs)

    assert await updates.run_async(args={}, tool_context=ctx) == {"requests": []}
