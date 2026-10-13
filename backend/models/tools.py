"""I/O models for the photo-reading agent tools (SPEC §6). The other tools' models arrive with their tasks.

A photo answer has two parts: fixed fields that code branches on (null when not legible), and a short
list of observations for anything else worth knowing. The list is trimmed here, not by the prompt, so a
chatty model reply cannot flood the agent's context."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from models.ws import MediaKind

MIN_CONFIDENCE = 0.6
MAX_OBSERVATIONS = 6

Confidence = Annotated[float, Field(ge=0, le=1)]


class Observation(BaseModel):
    label: str
    value: str
    confidence: Confidence


def _surest(items: list[Observation]) -> list[Observation]:
    kept = [o for o in items if o.confidence >= MIN_CONFIDENCE]
    return sorted(kept, key=lambda o: o.confidence, reverse=True)[:MAX_OBSERVATIONS]


Observations = Annotated[list[Observation], AfterValidator(_surest)]


class IdentifyIn(BaseModel):
    media_uri: str


class IdentifyOut(BaseModel):
    brand: str | None
    model: str | None
    series: str | None
    type: str | None
    error_code: str | None
    confidence: Confidence
    observations: Observations = []


class RequestMediaIn(BaseModel):
    kind: MediaKind
    target: str
    reason: str
    framing_tip: str


class RequestMediaOut(BaseModel):
    media_uri: str
    findings: Observations
    matches_expected: bool
    confidence: Confidence
    follow_up: str | None
