"""Shapes shared by repair steps, safety gates and fault cards (SAFETY.md, firestore.md `jobs`, fault_card.schema.json).
Defined once here; the Job, FaultCard and WebSocket models import them."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Hazard = Literal["none", "HV", "capacitor", "refrigerant"]
ApplianceType = Literal[
    "split_ac", "window_ac", "fridge", "washing_machine", "led_tv", "microwave", "geyser", "fan_cooler", "other"
]
GateId = Literal["G_MAINS_OFF", "G_CAP_DISCHARGE"]
GateState = Literal["open", "passed", "failed"]
MediaKind = Literal["photo", "video", "document"]
Confidence = Annotated[float, Field(ge=0, le=1)]
# Hard stops (SAFETY.md): a step with one of these is never emitted. The hazard levels above do not change.
StopReason = Literal["refrigerant", "microwave_hv", "crt", "geyser_open"]


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
    reason: Literal["requested", "side_issue", "manual"] | None = None


class RepairJob(BaseModel):
    """The part of `jobs/{jid}` the repair, gate and media tools read and write. A new job has all gates open."""

    model_config = ConfigDict(extra="forbid")
    job_id: str
    steps: list[RepairStep] = []
    gates: dict[GateId, GateState] = {"G_MAINS_OFF": "open", "G_CAP_DISCHARGE": "open"}
    current_step: Annotated[int, Field(ge=0)] = 0
    media: list[JobMedia] = []
