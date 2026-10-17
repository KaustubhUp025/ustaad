"""request_quotes as the Live agent calls it: the job and worker come from session state, never from the model; the
rules are tools/quotes.py; each saved vendor gets the request on Telegram, and the phone gets the `quotes` frame
whose quote_request_id the job screen polls."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from agent.media_tools import MediaDesk
from clients.firestore import QuoteStore
from clients.telegram import TelegramBot
from models.quotes import RequestQuotesOut
from models.ws import QuoteItem, Quotes
from tools import quotes

logger = logging.getLogger(__name__)


def quote_tools(store: QuoteStore, bot: TelegramBot, desk: MediaDesk) -> list[FunctionTool]:
    async def request_quotes(tool_context: ToolContext, part: str, specs: str = "", qty: int = 1) -> dict:
        """Asks his saved parts shops for a price and delivery time, when a part he needs is not in stock (check
        stock first). `part` as he names it, `specs` the model or rating if known. The replies arrive on his job
        screen; tell him who it went to. Empty `vendors`: he has no saved shops."""
        vendors = store.vendors(tool_context.state["worker_id"])
        if not vendors:
            return RequestQuotesOut(quote_request_id=None, vendors=[]).model_dump(mode="json")
        now = datetime.now(UTC)
        request, docs = quotes.new_request(
            f"qr_{uuid4().hex[:10]}",
            tool_context.state["job_id"],
            tool_context.state["worker_id"],
            part,
            specs,
            qty,
            vendors,
            now,
        )
        store.create(request, docs)
        reached = []
        for quote in docs:
            try:
                message_id = await bot.send_message(
                    quote.tg_chat_id, quotes.request_text(request), quotes.buttons(quote.id)
                )
            except RuntimeError:
                # A vendor who blocked the bot or never pressed Start; the others still get the request.
                logger.warning("quote request not delivered to vendor %s", quote.vendor_id)
                continue
            reached.append(
                store.update_quote(request.id, quote.id, lambda q, m=message_id: quotes.sent(q, m, now))
            )
        await desk.show(
            Quotes(
                quote_request_id=request.id,
                items=[
                    QuoteItem(
                        quote_id=q.id,
                        vendor=q.vendor_name,
                        distance_km=None,
                        price_inr=q.price_inr,
                        available=q.available,
                        eta=q.eta,
                        from_voice=q.from_voice,
                    )
                    for q in reached
                ],
            )
        )
        return RequestQuotesOut(
            quote_request_id=request.id, vendors=[q.vendor_name for q in reached]
        ).model_dump(mode="json")

    tool = FunctionTool(request_quotes)
    tool.behavior = types.Behavior.NON_BLOCKING
    tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return [tool]
