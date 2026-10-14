"""Inventory entity and REST payloads; persistence and voice adaptation live at their boundaries."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator

Nonblank = Annotated[str, Field(strict=True, pattern=r"\S")]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]


def _nonzero(value: int) -> int:
    if value == 0:
        raise ValueError("delta must be nonzero")
    return value


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(strict=True, pattern=r"^part_\S+$")]
    name: Nonblank
    category: Nonblank | None
    aliases: list[Nonblank]
    qty: NonnegativeInt
    min_qty: NonnegativeInt
    unit_cost_inr: NonnegativeInt | None
    source: Literal["voice", "photo", "manual"]
    updated_at: AwareDatetime

    @field_validator("updated_at", mode="before")
    @classmethod
    def timestamp_input(cls, value):
        # Pydantic also accepts epoch numbers; the contract requires an ISO timestamp.
        if not isinstance(value, (str, datetime)):
            raise ValueError("updated_at must be an ISO timestamp or datetime")  # noqa: TRY004 — Pydantic validation
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    @field_validator("updated_at")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("updated_at must be UTC")
        return value


class InventoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[InventoryItem]


class InventoryDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    part: Nonblank
    delta: Annotated[int, Field(strict=True), AfterValidator(_nonzero)]


class InventoryDeltaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deltas: Annotated[list[InventoryDelta], Field(min_length=1)]
