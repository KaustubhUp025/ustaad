"""Shapes shared by repair steps, safety gates and fault cards (SAFETY.md, firestore.md `jobs`, fault_card.schema.json).
Defined once here; the Job, FaultCard and WebSocket models import them."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Hazard = Literal["none", "HV", "capacitor", "refrigerant"]
ApplianceType = Literal[
    "split_ac", "window_ac", "fridge", "washing_machine", "led_tv", "microwave", "geyser", "fan_cooler", "other"
]
# A worker's profile trades (firestore.md `workers.trades[]`) and the card types each covers (SPEC §6).
Trade = Literal["ac", "fridge", "washing_machine", "led_tv", "microwave", "geyser", "fan_cooler", "other"]
TRADE_TYPES: dict[Trade, list[ApplianceType]] = {
    "ac": ["split_ac", "window_ac"],
    **{t: [t] for t in ("fridge", "washing_machine", "led_tv", "microwave", "geyser", "fan_cooler", "other")},
}
GateId = Literal["G_MAINS_OFF", "G_CAP_DISCHARGE"]
GateState = Literal["open", "passed", "failed"]
JobStatus = Literal["open", "guiding", "waiting_part", "closed"]
MediaKind = Literal["photo", "video", "document"]
# Why a photo is on the job: Ustaad asked for it, or the worker sent it himself (a side issue or a manual page).
MediaReason = Literal["requested", "side_issue", "manual"]
Confidence = Annotated[float, Field(ge=0, le=1)]
# Hard stops (SAFETY.md): a step with one of these is never emitted. The hazard levels above do not change.
# `power_on` is for general steps only: a voltage, supply or live test comes only from a fault card or manual.
StopReason = Literal["refrigerant", "microwave_hv", "crt", "geyser_open", "power_on"]


class StepSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["whatsapp_voice", "whatsapp_text", "manual", "job", "synthetic", "manual_photo", "general"]
    label: str
    audio_uri: str | None
    doc: str | None
    page: int | None


class Observation(BaseModel):
    label: str
    value: str
    confidence: Confidence


class RepairStep(BaseModel):
    """One entry of `jobs.steps[]`."""

    model_config = ConfigDict(extra="forbid")
    n: Annotated[int, Field(ge=1)]
    instruction: str
    # Display-only English of `instruction`; never decides hazard, gates or order.
    instruction_en: str | None = None
    # Display-only translation into the job's `translation_lang`; never decides hazard, gates or order.
    instruction_translated: str | None = None
    hazard: Hazard
    source: StepSource


class JobMedia(BaseModel):
    """One entry of `jobs.media[]`: a photo or clip the server asked for and checked."""

    model_config = ConfigDict(extra="forbid")
    request_id: str
    uri: str
    kind: MediaKind
    findings: list[Observation]
    confidence: Confidence
    reason: MediaReason | None = None


class PartUsed(BaseModel):
    """One entry of `jobs.parts_used[]`."""

    model_config = ConfigDict(extra="forbid")
    part: str
    qty: Annotated[int, Field(ge=1)]


class RepairJob(BaseModel):
    """The part of `jobs/{jid}` the repair, gate and media tools read and write. A new job has all gates open."""

    model_config = ConfigDict(extra="forbid")
    job_id: str
    steps: list[RepairStep] = []
    gates: dict[GateId, GateState] = {"G_MAINS_OFF": "open", "G_CAP_DISCHARGE": "open"}
    current_step: Annotated[int, Field(ge=0)] = 0
    media: list[JobMedia] = []
    # Set by close_job (T22).
    status: JobStatus = "open"
    outcome: str | None = None
    parts_used: list[PartUsed] = []
    closed_at: AwareDatetime | None = None
    # BCP-47 code of every step's instruction_translated; None while the steps have no translation.
    translation_lang: str | None = None
