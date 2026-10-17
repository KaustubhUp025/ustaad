"""I/O models for the agent tools (SPEC §6): the photo-reading tools and the repair tools. The other tools'
models arrive with their tasks.

A photo answer has two parts: fixed fields that code branches on (null when not legible), and a short
list of observations for anything else worth knowing. The list is trimmed here, not by the prompt, so a
chatty model reply cannot flood the agent's context."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, computed_field, model_validator

from models.repair import (
    ApplianceType,
    Confidence,
    GateId,
    Hazard,
    MediaKind,
    Observation,
    PartUsed,
    RepairStep,
    StepSource,
    StopReason,
)

MIN_CONFIDENCE = 0.6
MAX_OBSERVATIONS = 6


def _surest(items: list[Observation]) -> list[Observation]:
    kept = [o for o in items if o.confidence >= MIN_CONFIDENCE]
    return sorted(kept, key=lambda o: o.confidence, reverse=True)[:MAX_OBSERVATIONS]


Observations = Annotated[list[Observation], AfterValidator(_surest)]


class IdentifyIn(BaseModel):
    media_uri: str


class NameplateRead(BaseModel):
    """What Flash vision reads from a nameplate or error display; tools/identify.py normalises it."""

    brand: str | None
    model: str | None
    series: str | None
    type: str | None
    error_code: str | None
    confidence: Confidence
    observations: list[Observation]


class IdentifyOut(BaseModel):
    brand: str | None
    model: str | None
    series: str | None
    type: ApplianceType | None
    error_code: str | None
    confidence: Confidence
    observations: Observations = []

    @computed_field
    @property
    def readable(self) -> bool:
        """False: the agent asks for a clearer photo, or the nameplate, instead of using the reading (BUILD-GUIDE T12).
        A sure reading of a photo with no brand, model or code on it is not usable either."""
        return self.confidence >= MIN_CONFIDENCE and any((self.brand, self.model, self.error_code))


class RequestMediaIn(BaseModel):
    kind: MediaKind
    target: str
    reason: str
    framing_tip: str
    # Set when the photo is a safety gate's evidence: the gate check then judges it (docs/SAFETY.md).
    gate_id: GateId | None = None


class MediaCheck(BaseModel):
    """What Flash vision reads from a requested photo. Code, not the model, decides whether to ask for a retake."""

    matches_expected: bool
    confidence: Confidence
    problem: Literal["blurry", "dark", "not_visible"] | None
    findings: list[Observation]


class RequestMediaOut(BaseModel):
    media_uri: str | None
    findings: Observations
    matches_expected: bool
    confidence: Confidence
    follow_up: str | None
    # True while the same request waits for his retake: the next photo arrives on its own.
    retaking: bool = False


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
    translation_lang: str | None = None


class StepTranslations(BaseModel):
    """Flash's translation of a job's steps: one line per step, in order."""

    lines: list[str]


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


class SearchFaultCardsIn(BaseModel):
    brand: str
    model: str | None = None
    error_code: str | None = None
    symptom: str | None = None
    # Only cards of this type; a card without a type is left out, since it may be any appliance (T41).
    appliance_type: ApplianceType | None = None


class Citation(BaseModel):
    author: str | None
    date: str | None
    audio_uri: str | None


class CardHit(BaseModel):
    """A found card without its step text: steps reach the model only through next_step (BUILD-GUIDE §6.5)."""

    card_id: str
    brand: str
    model: str | None
    error_code: str
    symptom: str
    root_cause: str | None
    hazard: Hazard
    steps: int
    confidence: Confidence
    verified_count: int
    citation: Citation


class SearchFaultCardsOut(BaseModel):
    cards: list[CardHit]


StockErrorReason = Literal["unknown_part", "ambiguous_part", "below_zero"]


class StockLine(BaseModel):
    """One part's stock as the agent and the `stock` frame see it."""

    part: str
    qty: int
    min_qty: int
    low: bool


class CheckInventoryOut(BaseModel):
    # Empty: he doesn't stock it. More than one: ask which he means.
    items: list[StockLine]


class InventoryUpdated(BaseModel):
    status: Literal["UPDATED"] = "UPDATED"
    items: list[StockLine]


class InventoryNotUpdated(BaseModel):
    status: Literal["NOT_UPDATED"] = "NOT_UPDATED"
    reason: StockErrorReason | Literal["bad_delta"]
    part: str


class CloseJobIn(BaseModel):
    """The worker's two closing answers (what caused it, what fixed it) and what Ustaad knows of the job. The job
    record holds no brand or code, so Ustaad passes them."""

    symptom: str
    outcome: str
    fix_summary: str
    parts_used: list[PartUsed] = []
    brand: str | None = None
    error_code: str | None = None
    appliance_type: ApplianceType | None = None


class Closed(BaseModel):
    status: Literal["CLOSED"] = "CLOSED"
    card_id: str


class AlreadyClosed(BaseModel):
    status: Literal["ALREADY_CLOSED"] = "ALREADY_CLOSED"
