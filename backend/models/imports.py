"""Shapes of the WhatsApp import pipeline (SPEC §4): a thread's messages going into card extraction, the card draft
Flash returns, and the counts written to `imports/{id}`."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from models.fault_card import FaultCardPart
from models.repair import ApplianceType, Confidence, Hazard

ImportStatus = Literal["queued", "parsing", "transcribing", "extracting", "done", "failed"]


class Import(BaseModel):
    """The public `imports/{id}` document (rest.md, firestore.md)."""

    id: Annotated[str, Field(strict=True, pattern=r"^i_\S+$")]
    worker_id: str
    group_name: str | None = None
    status: ImportStatus
    files_total: Annotated[int, Field(strict=True, ge=0)]
    audio_total: Annotated[int, Field(strict=True, ge=0)]
    audio_done: Annotated[int, Field(strict=True, ge=0)]
    threads: Annotated[int, Field(strict=True, ge=0)]
    cards_created: Annotated[int, Field(strict=True, ge=0)]
    cards_needing_review: Annotated[int, Field(strict=True, ge=0)]
    errors: list[str]
    started_at: AwareDatetime | None
    finished_at: AwareDatetime | None


class ThreadMessage(BaseModel):
    """One eligible message of a thread (BUILD-GUIDE T13 step 4)."""

    id: str
    speaker: str
    ts: AwareDatetime
    kind: Literal["text", "voice", "photo"]
    # The message text, the voice note's transcript, or the photo's description.
    text: str
    # Voice only; None until the note's FLAC is stored.
    audio_uri: str | None = None

    @model_validator(mode="after")
    def audio_only_on_voice(self) -> "ThreadMessage":
        if self.audio_uri is not None and self.kind != "voice":
            raise ValueError("only a voice message has audio_uri")
        return self


class DraftStep(BaseModel):
    text: str
    summary_en: str
    hazard: Hazard


class CardDraft(BaseModel):
    """What Flash reads from one thread (BUILD-GUIDE §7.4). Code, not the model, decides credit and review."""

    resolved: bool
    brand: str | None
    model: str | None
    appliance_type: ApplianceType | None
    error_code: str | None
    symptom: str | None
    root_cause: str | None
    symptom_en: str | None = None
    root_cause_en: str | None = None
    steps: list[DraftStep]
    parts: list[FaultCardPart]
    # The message that states the fix; its speaker is credited.
    fix_message_id: str | None
    message_ids: list[str]
    confidence: Confidence
    language: str | None


class CardCounts(BaseModel):
    cards_created: int = 0
    cards_merged: int = 0
    cards_needing_review: int = 0
    errors: list[str] = []
