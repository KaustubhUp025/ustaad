"""GET /api/quotes/{qrid} and POST /api/quotes/{qid}/approve (rest.md): the worker's quotes, ranked, as the job
screen polls them; approving one confirms it to that vendor on Telegram."""

import os
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.session import require_session
from clients.firestore import QuoteStore
from clients.telegram import TelegramBot, telegram_bot
from models.quotes import SERVER_ONLY, Quote, QuoteDoc, QuoteRequest, QuotesResponse
from tools import quotes

router = APIRouter(prefix="/api/quotes")


@cache
def quote_store() -> QuoteStore:
    return QuoteStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


Store = Annotated[QuoteStore, Depends(quote_store)]
Bot = Annotated[TelegramBot, Depends(telegram_bot)]
WorkerId = Annotated[str, Depends(require_session)]


def _response(request: QuoteRequest, docs: list[QuoteDoc], now: datetime) -> QuotesResponse:
    request, docs = quotes.on_read(request, docs, now)
    return QuotesResponse(
        request=request,
        quotes=[Quote.model_validate(q.model_dump(exclude=SERVER_ONLY)) for q in quotes.rank(docs)],
    )


@router.get("/{qrid}", response_model=QuotesResponse)
def get_quotes(qrid: str, store: Store, worker_id: WorkerId) -> QuotesResponse:
    found = store.get(qrid)
    if found is None or found[0].worker_id != worker_id:
        raise HTTPException(404)
    return _response(*found, datetime.now(UTC))


@router.post("/{qid}/approve", response_model=QuotesResponse)
async def approve_quote(qid: str, store: Store, bot: Bot, worker_id: WorkerId) -> QuotesResponse:
    now = datetime.now(UTC)
    found = store.find(qid, now)
    if found is None or found[0].worker_id != worker_id:
        raise HTTPException(404)
    try:
        request, quote = store.approve(found[0].id, qid, lambda r, q: quotes.approve(r, q, now))
    except (quotes.IllegalTransition, quotes.RequestClosed) as err:
        raise HTTPException(409) from err
    await bot.send_message(quote.tg_chat_id, quotes.confirm_text(request, quote))
    return _response(*store.get(request.id), now)
