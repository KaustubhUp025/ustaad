"""Internal T13 parser models shared with later import stages."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.imports import ThreadMessage

MessageId = Annotated[str, Field(pattern=r"^m[1-9][0-9]*$")]


class Attachment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Annotated[str, Field(min_length=1)]
    kind: Literal["audio", "photo", "video", "file"]
    available: bool


class ExportMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: MessageId
    speaker: Annotated[str, Field(min_length=1)]
    timestamp: datetime
    text: str
    attachment: Attachment | None = None
    export_index: Annotated[int, Field(ge=0)]

    @field_validator("timestamp")
    @classmethod
    def local_wall_clock_only(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("export timestamps must remain local wall-clock values")
        return value


class ParsedChat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["android", "ios"]
    date_order: Literal["day_first", "month_first"]
    messages: list[ExportMessage]


class MessageEnrichment(BaseModel):
    """Offline result supplied by a media enrichment stage before threading."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    audio_uri: str | None = None


class PreparationResult(BaseModel):
    """T13 output; the later Import writer appends `errors` to `imports.errors`."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ThreadMessage]
    errors: list[str] = Field(default_factory=list)


class Threads(BaseModel):
    model_config = ConfigDict(extra="forbid")

    groups: list[list[str]]
