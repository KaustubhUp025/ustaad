"""The Telegram Bot API over plain httpx: vendor quote requests go out and their voice notes come in through it
(DECISIONS, Oct 17). The token is part of every URL, so errors name the method only."""

import os
from functools import cache

import httpx

from models.telegram import Button

API = "https://api.telegram.org"


class TelegramBot:
    def __init__(self, token: str, http: httpx.AsyncClient) -> None:
        self._token = token
        self._http = http

    async def _call(self, method: str, **params) -> dict | bool:
        response = await self._http.post(f"{API}/bot{self._token}/{method}", json=params)
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(
                f"Telegram {method} failed: {response.status_code} {body.get('description', '')}"
            )
        return body["result"]

    async def send_message(self, chat_id: int, text: str, buttons: list[Button] = ()) -> int:
        params: dict = {"chat_id": chat_id, "text": text}
        if buttons:
            params["reply_markup"] = {
                "inline_keyboard": [[{"text": b.text, "callback_data": b.data} for b in buttons]]
            }
        return (await self._call("sendMessage", **params))["message_id"]

    async def answer_callback(self, callback_id: str) -> None:
        """Stops the vendor's button spinning."""
        await self._call("answerCallbackQuery", callback_query_id=callback_id)

    async def download_file(self, file_id: str) -> bytes:
        path = (await self._call("getFile", file_id=file_id))["file_path"]
        response = await self._http.get(f"{API}/file/bot{self._token}/{path}")
        if response.status_code != 200:
            raise RuntimeError(f"Telegram file download failed: {response.status_code}")
        return response.content


@cache
def telegram_bot() -> TelegramBot:
    return TelegramBot(os.environ["TG_BOT_TOKEN"], httpx.AsyncClient(timeout=20))
