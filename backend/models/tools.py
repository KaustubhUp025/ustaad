"""I/O models for the agent tools (SPEC §6): the photo-reading tools and the repair tools. The other tools'
models arrive with their tasks.

A photo answer has two parts: fixed fields that code branches on (null when not legible), and a short
list of observations for anything else worth knowing. The list is trimmed here, not by the prompt, so a
chatty model reply cannot flood the agent's context."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, model_validator

from models.repair import GateId, Hazard, RepairStep, StepSource, StopReason
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


# Repair tools. The job ID is not an input: the tools take it from the session, so the model cannot pick a job.


class ProposedStep(BaseModel):
    """A general step the Live model proposes when no card or manual matched (SPEC §6, general steps)."""

    instruction: str
    summary_en: str


class StartRepairIn(BaseModel):
    card_ids: list[str] = []
    steps: list[ProposedStep] = []

    @model_validator(mode="after")
    def cards_or_steps(self) -> "StartRepairIn":
        if bool(self.card_ids) == bool(self.steps):
            raise ValueError("pass card_ids or proposed steps, not both and not neither")
        return self


class PlannedStep(BaseModel):
    """A stored step as the model first sees it: no instruction text, so a hazardous step cannot be spoken before
    its gate (BUILD-GUIDE §6.5). The text comes only from next_step."""

    n: int
    hazard: Hazard
    source: StepSource


class Started(BaseModel):
    status: Literal["STARTED"] = "STARTED"
    of: int
    steps: list[PlannedStep]


class StopRefer(BaseModel):
    status: Literal["STOP_REFER"] = "STOP_REFER"
    reason: StopReason


class StepOut(BaseModel):
    status: Literal["STEP"] = "STEP"
    job_id: str
    of: int
    step: RepairStep


class SafetyGateOut(BaseModel):
    status: Literal["SAFETY_GATE"] = "SAFETY_GATE"
    gate_id: GateId
    required_evidence: str


class RepairDone(BaseModel):
    status: Literal["DONE"] = "DONE"


class ConfirmSafetyIn(BaseModel):
    gate_id: GateId
    media_uri: str


class GateCheck(BaseModel):
    """What Flash vision reads from a gate photo. Code, not the model, decides whether the gate passes."""

    passed: bool
    reason: str | None
    confidence: Confidence
    reading_volts: float | None = None


class ConfirmSafetyOut(BaseModel):
    gate_id: GateId
    passed: bool
    reason: str | None
