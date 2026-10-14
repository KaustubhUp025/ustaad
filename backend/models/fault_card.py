"""Fault-card shapes that do not depend on the shared repair models."""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FaultCardSource(BaseModel):
    """The source object from fault_card.schema.json, distinct from repair StepSource."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["whatsapp_voice", "whatsapp_text", "manual", "job", "synthetic"]
    author: str | None = None
    date: Date | None = None
    message_ids: list[str] | None = None
    doc: str | None = None
    page: int | None = Field(default=None, strict=True)
    audio_uri: str | None = None


class FaultCardPart(BaseModel):
    """One entry of FaultCard.parts from fault_card.schema.json."""

    model_config = ConfigDict(extra="forbid")

    name: str
    part_no: str | None = None
