"""Public FaultCard contract from shared/contracts/fault_card.schema.json."""

from datetime import date as Date
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from models.repair import ApplianceType, Hazard

StrictString = Annotated[str, Field(strict=True)]
ReviewStatus = Literal["auto", "needs_review", "approved", "rejected"]


class FaultCardSource(BaseModel):
    """The source object from fault_card.schema.json, distinct from repair StepSource."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["whatsapp_voice", "whatsapp_text", "manual", "job", "synthetic"]
    author: StrictString = None
    date: Date = None
    message_ids: list[StrictString] = Field(default=None, strict=True)
    doc: StrictString = None
    page: int = Field(default=None, strict=True)
    audio_uri: StrictString = None

    @field_validator("date", mode="before")
    @classmethod
    def date_input(cls, value):
        if not isinstance(value, str):
            raise ValueError("date must be a YYYY-MM-DD string")  # noqa: TRY004 — Pydantic validation
        try:
            parsed = Date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("date must be a YYYY-MM-DD string") from exc
        if parsed.isoformat() != value:
            raise ValueError("date must be a YYYY-MM-DD string")
        return parsed


class FaultCardPart(BaseModel):
    """One entry of FaultCard.parts from fault_card.schema.json."""

    model_config = ConfigDict(extra="allow")

    name: StrictString
    part_no: StrictString = None


class FaultCard(BaseModel):
    """Public REST entity; Firestore's server-only embedding is deliberately absent."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(strict=True, pattern=r"^fc_\S+$")]
    worker_id: StrictString = None
    created_at: AwareDatetime
    photo_uri: StrictString = None
    brand: StrictString
    model: StrictString = None
    series: StrictString = None
    year_range: StrictString = None
    appliance_type: ApplianceType = None
    error_code: StrictString
    symptom: StrictString
    root_cause: StrictString = None
    fix_steps: list[StrictString] = Field(strict=True, min_length=1)
    # Display-only English beside the words as said; never read by hazard, gate or step-order code.
    symptom_en: StrictString = None
    root_cause_en: StrictString = None
    fix_steps_en: list[StrictString] = Field(default=None, strict=True)
    parts: list[FaultCardPart] = Field(default=None, strict=True)
    hazard: Hazard
    source: FaultCardSource
    confidence: float = Field(strict=True, ge=0, le=1)
    verified_count: int = Field(default=1, strict=True, ge=0)
    language: StrictString = None
    review_status: ReviewStatus = None

    @model_validator(mode="after")
    def english_step_for_each_step(self) -> "FaultCard":
        if self.fix_steps_en is not None and len(self.fix_steps_en) != len(self.fix_steps):
            raise ValueError("fix_steps_en must have exactly one item per fix_steps item")
        return self

    def to_public_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude_unset=True, exclude_none=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def timestamp_input(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("created_at must be an ISO timestamp or datetime")  # noqa: TRY004 — Pydantic validation
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    @field_validator("created_at")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("created_at must be UTC")
        return value
