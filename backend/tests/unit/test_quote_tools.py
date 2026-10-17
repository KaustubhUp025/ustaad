"""request_quotes as the Live agent calls it (SPEC §6, BUILD-GUIDE T19): the job and worker come from session state;
one quote per saved vendor; each vendor gets the request with its two buttons; the phone gets the `quotes` frame."""

from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk
from agent.quote_tools import quote_tools
from tests.unit.fake_quotes import FakeBot, FakeQuoteStore


class Desk(MediaDesk):
    def __init__(self) -> None:
        super().__init__("j_1", "bucket")
        self.shown = []

    async def show(self, frame) -> None:
        self.shown.append(frame)


def setup(bot=None):
    store, bot, desk = FakeQuoteStore(), bot or FakeBot(), Desk()
    (tool,) = quote_tools(store, bot, desk)
    return store, bot, desk, tool, SimpleNamespace(state={"worker_id": "w_hi_demo", "job_id": "j_1"})


def test_request_quotes_is_non_blocking_and_answers_when_idle():
    *_, tool, _ = setup()
    assert (tool.name, tool.behavior) == ("request_quotes", types.Behavior.NON_BLOCKING)
    assert tool.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


async def test_pcb_nahi_hai_sends_the_request_to_every_saved_vendor():
    store, bot, desk, tool, ctx = setup()
    out = await tool.run_async(
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

    store, _, _, tool, ctx = setup(BlockedB())
    out = await tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out["vendors"] == ["Vendor A", "Vendor C"]
    _, docs = store.get(out["quote_request_id"])
    assert [q.state for q in docs] == ["SENT", "CREATED", "SENT"]


async def test_no_saved_vendors():
    store, bot, desk, tool, ctx = setup()
    store.vendor_list = []
    out = await tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out == {"quote_request_id": None, "vendors": []}
    assert (store.requests, bot.sent, desk.shown) == ({}, [], [])
