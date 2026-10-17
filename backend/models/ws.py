"""Live WebSocket frames, one model per row of shared/contracts/ws-events.md (protocol v1)."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from models.repair import GateId, Hazard, MediaKind, StepSource


class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: Literal[1] = 1


# Client → server


class Ptt(Frame):
    type: Literal["ptt"] = "ptt"
    state: Literal["start", "end"]


class MediaReady(Frame):
    type: Literal["media_ready"] = "media_ready"
    request_id: str
    uri: str
    kind: MediaKind


class MediaCancel(Frame):
    type: Literal["media_cancel"] = "media_cancel"
    request_id: str


class MediaOffer(Frame):
    """The worker starts a photo himself; the server answers with a media_request it issues."""

    type: Literal["media_offer"] = "media_offer"
    kind: Literal["photo", "document"]


class Text(Frame):
    type: Literal["text"] = "text"
    text: str


class Ping(Frame):
    type: Literal["ping"] = "ping"


# Server → client


class SessionReady(Frame):
    type: Literal["session_ready"] = "session_ready"
    session_id: str
    live_model: str
    resumable: bool


class Caption(Frame):
    type: Literal["caption"] = "caption"
    who: Literal["user", "ustaad"]
    text: str
    final: bool


class TurnComplete(Frame):
    type: Literal["turn_complete"] = "turn_complete"


class Interrupted(Frame):
    type: Literal["interrupted"] = "interrupted"


class ProfileUpdate(Frame):
    type: Literal["profile_update"] = "profile_update"
    fields: dict[str, Any]


class Identified(Frame):
    type: Literal["identified"] = "identified"
    brand: str | None
    model: str | None
    error_code: str | None
    confidence: float


class StepCard(Frame):
    type: Literal["step_card"] = "step_card"
    job_id: str
    n: int
    of: int
    instruction: str
    instruction_translated: str | None = None
    hazard: Hazard
    source: StepSource


class MediaRequest(Frame):
    type: Literal["media_request"] = "media_request"
    request_id: str
    kind: MediaKind
    target: str
    framing_tip: str
    max_seconds: int | None


class MediaResult(Frame):
    type: Literal["media_result"] = "media_result"
    request_id: str
    matches_expected: bool
    confidence: float
    retake_reason: str | None


class SafetyGate(Frame):
    type: Literal["safety_gate"] = "safety_gate"
    gate_id: GateId
    message: str
    required_evidence: str


class GateResult(Frame):
    type: Literal["gate_result"] = "gate_result"
    gate_id: GateId
    passed: bool
    reason: str | None


class SafetyStop(Frame):
    type: Literal["safety_stop"] = "safety_stop"
    reason: str
    message: str


class ToolActivity(Frame):
    type: Literal["tool_activity"] = "tool_activity"
    label: str


class Stock(Frame):
    type: Literal["stock"] = "stock"
    part: str
    qty: int
    min_qty: int
    low: bool


class QuoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote_id: str
    vendor: str
    distance_km: float | None
    price_inr: int | None
    available: bool | None
    eta: str | None
    from_voice: bool


class Quotes(Frame):
    type: Literal["quotes"] = "quotes"
    quote_request_id: str
    items: list[QuoteItem]


class JobClosed(Frame):
    type: Literal["job_closed"] = "job_closed"
    job_id: str
    card_id: str


class ResumeHandle(Frame):
    type: Literal["resume_handle"] = "resume_handle"
    handle: str


class Pong(Frame):
    type: Literal["pong"] = "pong"


class Error(Frame):
    type: Literal["error"] = "error"
    code: Literal["live_unavailable", "rate_limited", "auth", "bad_request"]
    message: str


WsClientFrame = Annotated[Ptt | MediaReady | MediaCancel | MediaOffer | Text | Ping, Field(discriminator="type")]
WsServerFrame = Annotated[
    SessionReady
    | Caption
    | TurnComplete
    | Interrupted
    | ProfileUpdate
    | Identified
    | StepCard
    | MediaRequest
    | MediaResult
    | SafetyGate
    | GateResult
    | SafetyStop
    | ToolActivity
    | Stock
    | Quotes
    | JobClosed
    | ResumeHandle
    | Pong
    | Error,
    Field(discriminator="type"),
]

client_frame: TypeAdapter[WsClientFrame] = TypeAdapter(WsClientFrame)
server_frame: TypeAdapter[WsServerFrame] = TypeAdapter(WsServerFrame)
