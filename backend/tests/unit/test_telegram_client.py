"""The Telegram Bot API client against a fake transport: the requests it makes and what it returns. A failed call
never puts the bot token (which is part of the URL) in the error."""

import json

import httpx
import pytest

from clients.telegram import TelegramBot
from models.telegram import Button

TOKEN = "123:fake-token"


def bot_with(handler) -> tuple[TelegramBot, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return TelegramBot(TOKEN, httpx.AsyncClient(transport=httpx.MockTransport(record))), seen


async def test_send_message_with_buttons_returns_the_message_id():
    bot, seen = bot_with(lambda r: httpx.Response(200, json={"ok": True, "result": {"message_id": 77}}))
    message_id = await bot.send_message(1001, "hello", [Button(text="Available", data="avail:q_1")])
    assert message_id == 77
    (request,) = seen
    assert str(request.url) == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(request.content) == {
        "chat_id": 1001,
        "text": "hello",
        "reply_markup": {"inline_keyboard": [[{"text": "Available", "callback_data": "avail:q_1"}]]},
    }


async def test_send_message_without_buttons_has_no_keyboard():
    bot, seen = bot_with(lambda r: httpx.Response(200, json={"ok": True, "result": {"message_id": 78}}))
    await bot.send_message(1001, "confirmed")
    assert json.loads(seen[0].content) == {"chat_id": 1001, "text": "confirmed"}


async def test_answer_callback():
    bot, seen = bot_with(lambda r: httpx.Response(200, json={"ok": True, "result": True}))
    await bot.answer_callback("cb_1")
    assert (seen[0].url.path, json.loads(seen[0].content)) == (
        f"/bot{TOKEN}/answerCallbackQuery",
        {"callback_query_id": "cb_1"},
    )


async def test_download_file_looks_up_the_path_then_fetches_it():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "voice/file_1.oga"}})
        return httpx.Response(200, content=b"OggS")

    bot, seen = bot_with(handler)
    assert await bot.download_file("f_1") == b"OggS"
    assert json.loads(seen[0].content) == {"file_id": "f_1"}
    assert str(seen[1].url) == f"https://api.telegram.org/file/bot{TOKEN}/voice/file_1.oga"


async def test_a_failed_call_names_the_method_not_the_token():
    bot, _ = bot_with(
        lambda r: httpx.Response(403, json={"ok": False, "description": "Forbidden: bot was blocked"})
    )
    with pytest.raises(RuntimeError) as err:
        await bot.send_message(1001, "hello")
    assert "sendMessage" in str(err.value)
    assert TOKEN not in str(err.value)
