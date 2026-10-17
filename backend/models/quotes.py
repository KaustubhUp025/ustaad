"""Parts quotes (SPEC §7, firestore.md `quote_requests`, `quotes`, `vendors`): the stored documents, the REST
response, the parsed vendor reply and request_quotes' answer."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

from models.repair import Confidence

QuoteState = Literal["CREATED", "SENT", "PARSING", "CLARIFY", "QUOTED", "CONFIRMED", "DECLINED", "EXPIRED"]
RequestStatus = Literal["open", "approved", "expired"]


class Vendor(BaseModel):
    id: str
    name: str
    tg_chat_id: int


class QuoteRequest(BaseModel):
    id: str
    job_id: str
    worker_id: str
    part: str
    specs: str
    qty: Annotated[int, Field(ge=1)]
    vendor_ids: list[str]
    status: RequestStatus
    approved_quote_id: str | None
    created_at: AwareDatetime
    expires_at: AwareDatetime


class Quote(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    state: QuoteState
    price_inr: int | None
    available: bool | None
    eta: str | None
    eta_minutes: int | None
    from_voice: bool
    raw_text: str | None
    media_uri: str | None
    parsed_confidence: float | None
    updated_at: AwareDatetime


class QuoteDoc(Quote):
    """The stored quote: the REST `Quote` plus the server-only Telegram fields (rest.md)."""

    tg_chat_id: int
    tg_message_id: int | None


SERVER_ONLY = {"tg_chat_id", "tg_message_id"}


class QuotesResponse(BaseModel):
    request: QuoteRequest
    quotes: list[Quote]


class ParsedReply(BaseModel):
    """Flash's reading of one vendor reply."""

    price_inr: int | None
    available: bool | None
    eta: str | None
    eta_minutes: int | None
    confidence: Confidence


class RequestQuotesOut(BaseModel):
    """`vendors`: the names the request reached; empty (and no request) when he has no saved vendors."""

    quote_request_id: str | None
    vendors: list[str]


class NearbyShop(BaseModel):
    """A Places shop near the worker; not on the bot, so request_quotes cannot reach it."""

    name: str
    address: str | None
    distance_km: float | None


class FindVendorsOut(BaseModel):
    """`saved`: the shops request_quotes reaches; `nearby`: other shops from Places, nearest first."""

    saved: list[str]
    nearby: list[NearbyShop]


class QuoteUpdate(BaseModel):
    """The safe vendor fields the Live agent needs when the worker asks for quote updates."""

    vendor_name: str
    available: bool | None
    price_inr: int | None
    eta: str | None
    from_voice: bool


class QuoteRequestUpdate(BaseModel):
    status: RequestStatus
    quotes: list[QuoteUpdate]


class GetQuotesOut(BaseModel):
    requests: list[QuoteRequestUpdate]
