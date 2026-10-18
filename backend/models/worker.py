"""Worker entity (firestore.md `workers/{wid}`, rest.md Worker) and the demo session payloads."""

from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from models.repair import Trade

Lang = Literal["hi", "te", "ta", "bn", "en"]


def _distinct(trades: list[Trade]) -> list[Trade]:
    if len(set(trades)) != len(trades):
        raise ValueError("trades must not repeat")
    return trades


class Geo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lat: float
    lng: float


class Worker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(pattern=r"^w_\S+$")]
    name: str
    lang: Lang
    # Empty only while the onboarding interview is under way (firestore.md, T21).
    trades: Annotated[list[Trade], Field(max_length=3), AfterValidator(_distinct)]
    brands: list[str]
    pincode: str | None
    geo: Geo | None
    experience_yrs: int | None
    onboarding_done: bool
    skill_gaps: list[str]
    demo: bool
    created_at: AwareDatetime

    @model_validator(mode="after")
    def onboarded_with_a_trade(self) -> "Worker":
        if self.onboarding_done and not self.trades:
            raise ValueError("an onboarded worker has 1 to 3 trades")
        return self


class DemoSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = "w_hi_demo"
    # A new, empty demo worker for this visitor, for the onboarding interview (G1).
    onboarding: bool = False
    lang: Lang = "hi"

    @model_validator(mode="after")
    def fresh_worker_only(self) -> "DemoSessionRequest":
        # Onboarding always gets a new worker, so naming an existing one is a mistake, not a choice.
        if self.onboarding and "worker_id" in self.model_fields_set:
            raise ValueError("onboarding makes a new worker; do not send worker_id")
        return self


class StockAnswer(BaseModel):
    """A part he keeps, as he said it; `qty` 0 when he doesn't keep it, None when he gave no count."""

    part: str
    qty: Annotated[int, Field(ge=0)] | None = None


class SaveProfileIn(BaseModel):
    """One or more onboarding answers; a field left out is not changed."""

    trades: list[str] | None = None
    brands: list[str] | None = None
    pincode: str | None = None
    experience_yrs: int | None = None
    stock: list[StockAnswer] | None = None
    shop: str | None = None
    done: bool = False


class ProfileProblem(BaseModel):
    field: str
    reason: Literal[
        "pick_top_3", "unknown_trade", "duplicate_trade", "not_6_digits", "not_plausible", "missing"
    ]


class SaveProfileOut(BaseModel):
    status: Literal["SAVED", "ASK_AGAIN"]
    problems: list[ProfileProblem]
    onboarding_done: bool


class DemoSessionResponse(BaseModel):
    token: str
    worker: Worker
    ws_url: str
