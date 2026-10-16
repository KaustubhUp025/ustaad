"""Worker entity (firestore.md `workers/{wid}`, rest.md Worker) and the demo session payloads."""

from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

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
    trades: Annotated[list[Trade], Field(min_length=1, max_length=3), AfterValidator(_distinct)]
    brands: list[str]
    pincode: str | None
    geo: Geo | None
    experience_yrs: int | None
    onboarding_done: bool
    skill_gaps: list[str]
    demo: bool
    created_at: AwareDatetime


class DemoSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = "w_hi_demo"


class DemoSessionResponse(BaseModel):
    token: str
    worker: Worker
    ws_url: str
