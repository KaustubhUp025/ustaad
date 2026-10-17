"""POST /webhook/telegram (rest.md, BUILD-GUIDE T19) with Telegram and Flash faked: the secret header, dedupe on
update_id, the two buttons, text and voice replies parsed into quotes, and matching a reply to its quote."""

from datetime import UTC, datetime

import httpx
import pytest

from app.main import app
from app.quotes import quote_store
from app.telegram import PARSE_FAILED, reply_parser
from clients.telegram import telegram_bot
from models.quotes import ParsedReply
from tests.unit.fake_quotes import FakeBot, FakeQuoteStore, sent_request

SECRET = "test-webhook-secret"


class FakeParser:
    def __init__(self, reply: ParsedReply) -> None:
        self.reply = reply
        self.texts: list[str] = []
        self.voices: list[bytes] = []

    async def text(self, text: str) -> ParsedReply:
        self.texts.append(text)
        return self.reply

    async def voice(self, ogg: bytes) -> ParsedReply:
        self.voices.append(ogg)
        return self.reply


QUOTE_250 = ParsedReply(price_inr=250, available=True, eta="kal tak", eta_minutes=1440, confidence=0.9)


@pytest.fixture
def world(monkeypatch):
    monkeypatch.setenv("TG_WEBHOOK_SECRET", SECRET)
    store, bot, parser = FakeQuoteStore(), FakeBot(), FakeParser(QUOTE_250)
    request, docs = sent_request(now=datetime.now(UTC))
    store.create(request, docs)
    app.dependency_overrides.update(
        {quote_store: lambda: store, telegram_bot: lambda: bot, reply_parser: lambda: parser}
    )
    yield store, bot, parser, request.id
    app.dependency_overrides.clear()


async def post(update: dict, secret: str | None = SECRET) -> httpx.Response:
    headers = {"X-Telegram-Bot-Api-Secret-Token": secret} if secret is not None else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/webhook/telegram", json=update, headers=headers)


def message(update_id: int, chat_id: int, reply_to: int | None = None, **content) -> dict:
    msg = {"message_id": 10 + update_id, "chat": {"id": chat_id}} | content
    if reply_to is not None:
        msg["reply_to_message"] = {"message_id": reply_to, "chat": {"id": chat_id}}
    return {"update_id": update_id, "message": msg}


def tap(update_id: int, chat_id: int, data: str) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb_{update_id}",
            "data": data,
            "message": {"message_id": 500, "chat": {"id": chat_id}},
        },
    }


def quote_of(store, qrid, vendor_id):
    return next(q for q in store.quotes[qrid].values() if q.vendor_id == vendor_id)


@pytest.mark.parametrize("secret", [None, "wrong"])
async def test_a_bad_secret_is_403_and_changes_nothing(world, secret):
    store, _, parser, qrid = world
    response = await post(message(1, 1001, text="250"), secret)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert (store.seen_updates, parser.texts, quote_of(store, qrid, "v_a").state) == (set(), [], "SENT")


async def test_a_text_reply_becomes_a_quote(world):
    store, _, parser, qrid = world
    response = await post(message(1, 1001, text="250 rs piece, kal tak de dunga"))
    assert response.status_code == 200
    quote = quote_of(store, qrid, "v_a")
    assert parser.texts == ["250 rs piece, kal tak de dunga"]
    assert (quote.state, quote.price_inr, quote.eta, quote.from_voice, quote.raw_text) == (
        "QUOTED",
        250,
        "kal tak",
        False,
        "250 rs piece, kal tak de dunga",
    )


async def test_a_duplicate_update_is_handled_once(world):
    _, _, parser, _ = world
    await post(message(1, 1001, text="250"))
    await post(message(1, 1001, text="250"))
    assert parser.texts == ["250"]


async def test_a_voice_reply_is_downloaded_and_parsed(world):
    store, bot, parser, qrid = world
    await post(message(2, 1002, voice={"file_id": "f_1"}))
    quote = quote_of(store, qrid, "v_b")
    assert parser.voices == [bot.voice]
    assert (quote.state, quote.price_inr, quote.from_voice, quote.raw_text) == ("QUOTED", 250, True, None)


async def test_nahi_hai_declines(world):
    store, _, parser, qrid = world
    parser.reply = ParsedReply(price_inr=None, available=False, eta=None, eta_minutes=None, confidence=0.9)
    await post(message(3, 1003, text="nahi hai"))
    assert quote_of(store, qrid, "v_c").state == "DECLINED"


async def test_buttons_mark_available_and_decline(world):
    store, bot, _, qrid = world
    a, c = quote_of(store, qrid, "v_a"), quote_of(store, qrid, "v_c")
    await post(tap(4, 1001, f"avail:{a.id}"))
    await post(tap(5, 1003, f"na:{c.id}"))
    assert bot.answered == ["cb_4", "cb_5"]
    assert (quote_of(store, qrid, "v_a").state, quote_of(store, qrid, "v_a").available) == ("SENT", True)
    assert (quote_of(store, qrid, "v_c").state, quote_of(store, qrid, "v_c").available) == ("DECLINED", False)


async def test_a_button_for_another_vendors_quote_changes_nothing(world):
    store, bot, _, qrid = world
    await post(tap(6, 1001, f"na:{quote_of(store, qrid, 'v_b').id}"))
    assert bot.answered == ["cb_6"]
    assert quote_of(store, qrid, "v_b").state == "SENT"


async def test_a_reply_to_an_older_request_goes_to_that_request(world):
    store, _, _, new_qrid = world
    old_request, old_docs = sent_request("qr_old", datetime.now(UTC))
    old_docs = [q.model_copy(update={"tg_message_id": 700 + i}) for i, q in enumerate(old_docs)]
    store.create(
        old_request.model_copy(update={"created_at": old_request.created_at.replace(year=2025)}), old_docs
    )
    await post(message(7, 1001, reply_to=700, text="250"))
    assert quote_of(store, "qr_old", "v_a").state == "QUOTED"
    assert quote_of(store, new_qrid, "v_a").state == "SENT"
    await post(message(8, 1002, text="250"))
    assert (quote_of(store, new_qrid, "v_b").state, quote_of(store, "qr_old", "v_b").state) == (
        "QUOTED",
        "SENT",
    )


async def test_commands_and_unknown_chats_are_ignored(world):
    _, _, parser, _ = world
    await post(message(9, 1001, text="/start"))
    await post(message(10, 4242, text="250"))
    assert parser.texts == []


@pytest.mark.parametrize("content", [{"text": "250 rs, call 9999999999"}, {"voice": {"file_id": "f_secret"}}])
async def test_a_failed_parse_logs_one_fixed_line_and_leaves_the_quote_waiting(world, caplog, content):
    store, _, parser, qrid = world
    leak = "token=123:SYNTHETIC_TOKEN reply=250 rs"

    async def broken(_):
        raise RuntimeError(leak)

    parser.text = parser.voice = broken
    caplog.set_level("DEBUG")
    response = await post(message(11, 1001, **content))
    assert response.status_code == 200
    assert quote_of(store, qrid, "v_a").state == "SENT"
    assert [(r.getMessage(), r.exc_info) for r in caplog.records if r.name.startswith("app")] == [
        (PARSE_FAILED, None)
    ]
    # Every logger, not only ours (the test client's own request line is here too).
    for secret in (leak, "9999999999", "f_secret", qrid, quote_of(store, qrid, "v_a").id, "1001", SECRET):
        assert secret not in caplog.text


async def test_an_unclear_reply_gets_one_question_then_the_answer_is_read(world):
    store, bot, parser, qrid = world
    parser.reply = ParsedReply(price_inr=None, available=True, eta=None, eta_minutes=None, confidence=0.9)
    await post(message(12, 1001, text="haan hai"))
    await post(message(13, 1001, text="haan"))
    assert quote_of(store, qrid, "v_a").state == "CLARIFY"
    assert [(chat, text.splitlines()[0]) for chat, text, _ in bot.sent] == [(1001, f"Ustaad stock request #{qrid}")]
    assert "Sorry, we could not read the price" in bot.sent[0][1]
    parser.reply = QUOTE_250
    await post(message(14, 1001, text="250, kal tak"))
    assert (quote_of(store, qrid, "v_a").state, quote_of(store, qrid, "v_a").price_inr) == ("QUOTED", 250)
    assert len(bot.sent) == 1
