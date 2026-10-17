"""POST /webhook/telegram (rest.md): vendors' button taps, texts and voice notes become quotes. The secret header is
checked, Telegram gets its 200 at once, and each update is handled once in the background (backend/AGENTS.md)."""

import hmac
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.quotes import Bot, Store
from clients.audio import to_flac
from clients.firestore import QuoteStore
from clients.gemini import ask_json, hear_json
from clients.telegram import TelegramBot
from models.quotes import ParsedReply, QuoteDoc, QuoteRequest
from models.telegram import Message, Update
from tools import quotes

router = APIRouter()
logger = logging.getLogger(__name__)

QUESTION = (
    "This is a parts shop's reply, in Hindi, English or Hinglish, to a repair technician's request for a part's price "
    "per piece and delivery time. price_inr: the price per piece in whole rupees, null if no price is given. "
    'available: true if they have the part, false if they say they don\'t (for example "nahi hai"), null if unclear. '
    "eta: the delivery time in their words, null if not said. eta_minutes: that time in minutes from now, a whole "
    'number ("kal tak" is 1440, "1 ghante mein" is 60), null if not said. confidence 0-1: how sure you are of these '
    "fields."
)
# Fixed text: a vendor's reply, chat or quote IDs, the bot token or exception text must never reach the logs.
PARSE_FAILED = "vendor reply not parsed; the quote waits for the next reply"
UNREAD = ParsedReply(price_inr=None, available=None, eta=None, eta_minutes=None, confidence=0)


class ReplyParser:
    async def text(self, text: str) -> ParsedReply:
        return await ask_json(f"{QUESTION}\n\nTheir message: {text}", ParsedReply)

    async def voice(self, ogg: bytes) -> ParsedReply:
        return await hear_json(
            f"{QUESTION}\n\nTheir message is this voice note.", await to_flac(ogg), ParsedReply
        )


def reply_parser() -> ReplyParser:
    return ReplyParser()


def check_secret(
    token: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> None:
    if token is None or not hmac.compare_digest(token.encode(), os.environ["TG_WEBHOOK_SECRET"].encode()):
        raise HTTPException(403)


Parser = Annotated[ReplyParser, Depends(reply_parser)]


@router.post("/webhook/telegram", dependencies=[Depends(check_secret)])
async def telegram_webhook(
    update: Update, background: BackgroundTasks, store: Store, bot: Bot, parser: Parser
) -> dict:
    background.add_task(handle, update, store, bot, parser)
    return {"ok": True}


def _apply(
    store: QuoteStore, found: tuple[QuoteRequest, QuoteDoc], change: Callable[[QuoteDoc], QuoteDoc]
) -> QuoteDoc | None:
    """None when the quote has moved on (a late tap, a message while the last one is read): the update is dropped."""
    try:
        return store.update_quote(found[0].id, found[1].id, change)
    except quotes.IllegalTransition:
        logger.info("vendor update dropped: the quote is past it")
        return None


async def handle(update: Update, store: QuoteStore, bot: TelegramBot, parser: ReplyParser) -> None:
    if not store.first_delivery(update.update_id):
        return
    now = datetime.now(UTC)
    tap = update.callback_query
    if tap is not None:
        await bot.answer_callback(tap.id)
        action, _, quote_id = (tap.data or "").partition(":")
        found = tap.message and quotes.match(store.open_for_chat(tap.message.chat.id, now), quote_id=quote_id)
        if found:
            _apply(store, found, lambda q: quotes.pressed(q, action, now))
    elif update.message is not None:
        await _reply(update.message, store, bot, parser, now)


async def _reply(
    msg: Message, store: QuoteStore, bot: TelegramBot, parser: ReplyParser, now: datetime
) -> None:
    # /start and other bot commands are not replies.
    if (msg.text is None and msg.voice is None) or (msg.text or "").startswith("/"):
        return
    reply_to = msg.reply_to_message.message_id if msg.reply_to_message else None
    found = quotes.match(store.open_for_chat(msg.chat.id, now), reply_to=reply_to)
    if (
        found is None
        or _apply(store, found, lambda q: quotes.replied(q, msg.text, msg.voice is not None, now)) is None
    ):
        return
    try:
        reply = await (
            parser.voice(await bot.download_file(msg.voice.file_id)) if msg.voice else parser.text(msg.text)
        )
    except Exception:  # noqa: BLE001 — Flash, ffmpeg or download errors can carry the reply; only PARSE_FAILED is logged
        # Back to waiting, so the vendor's next message is still read.
        _apply(store, found, lambda q: quotes.parsed(q, UNREAD, datetime.now(UTC)))
        logger.warning(PARSE_FAILED)
        return
    _apply(store, found, lambda q: quotes.parsed(q, reply, datetime.now(UTC)))
