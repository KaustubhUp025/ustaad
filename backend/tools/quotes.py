"""The quote rules (SPEC §7, BUILD-GUIDE T19). Every state change goes through `transition`; expiry is computed on
read, because a serverless instance can disappear before any timer fires. Pure: the caller stores and sends."""

from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from models.quotes import ParsedReply, QuoteDoc, QuoteRequest, QuoteState, Vendor
from models.telegram import Button

EXPIRES_AFTER = timedelta(minutes=30)
# Below this, a parsed price is not trusted and the vendor's next message is read instead.
MIN_CONFIDENCE = 0.6

Event = Literal["sent", "reply", "available", "quoted", "unclear", "unread", "declined", "approved", "expired"]
TRANSITIONS: dict[tuple[QuoteState, Event], QuoteState] = {
    ("CREATED", "sent"): "SENT",
    ("SENT", "reply"): "PARSING",
    ("SENT", "available"): "SENT",
    ("SENT", "declined"): "DECLINED",
    ("PARSING", "available"): "PARSING",
    ("PARSING", "quoted"): "QUOTED",
    ("PARSING", "unclear"): "CLARIFY",
    # The parser failed, not the vendor: wait for his next message without asking him again.
    ("PARSING", "unread"): "SENT",
    ("PARSING", "declined"): "DECLINED",
    ("QUOTED", "available"): "QUOTED",
    ("QUOTED", "declined"): "DECLINED",
    ("QUOTED", "approved"): "CONFIRMED",
    ("CREATED", "expired"): "EXPIRED",
    ("SENT", "expired"): "EXPIRED",
    ("PARSING", "expired"): "EXPIRED",
    ("CLARIFY", "reply"): "PARSING",
    ("CLARIFY", "available"): "CLARIFY",
    ("CLARIFY", "declined"): "DECLINED",
    ("CLARIFY", "expired"): "EXPIRED",
}
ASK_AGAIN = (
    "Sorry, we could not read the price. Please reply with the price per piece in Rs and the delivery time, "
    "for example: 250, kal tak"
)
BUTTON_EVENTS: dict[str, Event] = {"avail": "available", "na": "declined"}


class IllegalTransition(ValueError):
    pass


class RequestClosed(ValueError):
    pass


def transition(state: QuoteState, event: Event) -> QuoteState:
    if (state, event) not in TRANSITIONS:
        raise IllegalTransition(f"{event} in {state}")
    return TRANSITIONS[(state, event)]


def _move(quote: QuoteDoc, event: Event, now: datetime, **fields) -> QuoteDoc:
    return quote.model_copy(update={"state": transition(quote.state, event), "updated_at": now} | fields)


def new_request(
    qrid: str,
    job_id: str,
    worker_id: str,
    part: str,
    specs: str,
    qty: int,
    vendors: list[Vendor],
    now: datetime,
) -> tuple[QuoteRequest, list[QuoteDoc]]:
    request = QuoteRequest(
        id=qrid,
        job_id=job_id,
        worker_id=worker_id,
        part=part,
        specs=specs,
        qty=qty,
        vendor_ids=[v.id for v in vendors],
        status="open",
        approved_quote_id=None,
        created_at=now,
        expires_at=now + EXPIRES_AFTER,
    )
    docs = [
        QuoteDoc(
            id=f"q_{uuid4().hex[:10]}",
            vendor_id=v.id,
            vendor_name=v.name,
            state="CREATED",
            price_inr=None,
            available=None,
            eta=None,
            eta_minutes=None,
            from_voice=False,
            raw_text=None,
            media_uri=None,
            parsed_confidence=None,
            updated_at=now,
            tg_chat_id=v.tg_chat_id,
            tg_message_id=None,
        )
        for v in vendors
    ]
    return request, docs


def request_text(request: QuoteRequest) -> str:
    lines = [f"Ustaad stock request #{request.id}", f"{request.part} x {request.qty}"]
    if request.specs:
        lines.append(f"Specs: {request.specs}")
    return "\n".join([*lines, "Please reply with price per piece and delivery time."])


def buttons(quote_id: str) -> list[Button]:
    return [
        Button(text="Available", data=f"avail:{quote_id}"),
        Button(text="Not available", data=f"na:{quote_id}"),
    ]


def sent(quote: QuoteDoc, message_id: int, now: datetime) -> QuoteDoc:
    return _move(quote, "sent", now, tg_message_id=message_id)


def pressed(quote: QuoteDoc, action: str, now: datetime) -> QuoteDoc:
    """A tap on one of the request's buttons: `avail` or `na`."""
    if action not in BUTTON_EVENTS:
        raise IllegalTransition(f"button {action}")
    return _move(quote, BUTTON_EVENTS[action], now, available=action == "avail")


def replied(quote: QuoteDoc, raw_text: str | None, from_voice: bool, now: datetime) -> QuoteDoc:
    return _move(quote, "reply", now, raw_text=raw_text, from_voice=from_voice)


def parsed(quote: QuoteDoc, reply: ParsedReply, now: datetime) -> QuoteDoc:
    said = {
        "eta": reply.eta or quote.eta,
        "eta_minutes": reply.eta_minutes if reply.eta_minutes is not None else quote.eta_minutes,
        "parsed_confidence": reply.confidence,
    }
    if reply.available is False:
        return _move(quote, "declined", now, available=False, **said)
    if reply.price_inr is not None and reply.confidence >= MIN_CONFIDENCE:
        return _move(quote, "quoted", now, price_inr=reply.price_inr, available=True, **said)
    return _move(quote, "unclear", now, available=reply.available or quote.available, **said)


def unread(quote: QuoteDoc, now: datetime) -> QuoteDoc:
    return _move(quote, "unread", now)


def ask_again(before: QuoteDoc, after: QuoteDoc) -> bool:
    """One follow-up question per quote (SPEC §7): only on the first move into CLARIFY."""
    return after.state == "CLARIFY" and before.state != "CLARIFY"


def clarify_text(request: QuoteRequest) -> str:
    return "\n".join(
        [
            f"Ustaad stock request #{request.id}",
            f"{request.part} x {request.qty}",
            ASK_AGAIN,
        ]
    )


def _expired(request: QuoteRequest, now: datetime) -> bool:
    return request.status == "open" and now >= request.expires_at


def on_read(
    request: QuoteRequest, docs: list[QuoteDoc], now: datetime
) -> tuple[QuoteRequest, list[QuoteDoc]]:
    """The request and its quotes as of `now`: past `expires_at`, an open request and its unanswered quotes are
    expired."""
    if not _expired(request, now):
        return request, docs
    return request.model_copy(update={"status": "expired"}), [
        _move(q, "expired", now) if (q.state, "expired") in TRANSITIONS else q for q in docs
    ]


def rank(docs: list[QuoteDoc]) -> list[QuoteDoc]:
    """Available first, then the lowest price, then the soonest delivery; unknowns last in each."""
    return sorted(
        docs,
        key=lambda q: (
            q.available is not True,
            q.price_inr is None,
            q.price_inr or 0,
            q.eta_minutes is None,
            q.eta_minutes or 0,
        ),
    )


def match(
    candidates: list[tuple[QuoteRequest, QuoteDoc]],
    *,
    quote_id: str | None = None,
    reply_to: int | None = None,
) -> tuple[QuoteRequest, QuoteDoc] | None:
    """Which of a vendor's open quotes a message is for: the button's quote, the quote whose request he replied to,
    else his newest quote still waiting for a reply (sent, or asked again)."""
    if quote_id is not None:
        return next((c for c in candidates if c[1].id == quote_id), None)
    replied_to = next(
        (c for c in candidates if reply_to is not None and c[1].tg_message_id == reply_to), None
    )
    waiting = [c for c in candidates if c[1].state in ("SENT", "CLARIFY")]
    return replied_to or max(waiting, key=lambda c: c[0].created_at, default=None)


def approve(request: QuoteRequest, quote: QuoteDoc, now: datetime) -> tuple[QuoteRequest, QuoteDoc]:
    if request.status != "open" or _expired(request, now):
        raise RequestClosed(request.id)
    confirmed = _move(quote, "approved", now)
    return request.model_copy(update={"status": "approved", "approved_quote_id": quote.id}), confirmed


def confirm_text(request: QuoteRequest, quote: QuoteDoc) -> str:
    lines = [
        f"Ustaad order #{request.id} confirmed",
        f"{request.part} x {request.qty} at Rs {quote.price_inr} per piece",
    ]
    if quote.eta:
        lines.append(f"Delivery: {quote.eta}")
    return "\n".join(lines)
