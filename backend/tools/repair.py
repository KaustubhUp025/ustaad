"""The repair tools (SPEC §6, docs/SAFETY.md): start_repair stores a job's steps, next_step hands them out one at
a time behind their gates, confirm_safety judges a gate photo. Pure: each takes the job and returns its answer
and the updated job; loading, saving and the vision call are the caller's."""

from models.fault_card import FaultCard
from models.repair import RepairJob, RepairStep, StepSource
from models.tools import (
    ConfirmSafetyIn,
    ConfirmSafetyOut,
    GateCheck,
    PlannedStep,
    RepairDone,
    SafetyGateOut,
    Started,
    StartRepairIn,
    StepOut,
    StopRefer,
)
from tools.gates import EVIDENCE, open_gate
from tools.hazard_tagger import tag

GENERAL = StepSource(kind="general", label="General guidance", audio_uri=None, doc=None, page=None)
MIN_GATE_CONFIDENCE = 0.7
MAX_DISCHARGED_VOLTS = 5.0
RETRY_MAINS = "Photo does not clearly show the MCB or isolator OFF, or the plug out. Send a clearer photo."
RETRY_DISCHARGE = (
    "Capacitor is not shown discharged. Discharge it safely with an insulated tool, then measure again and send "
    "a photo of the meter."
)


def _card_source(card: FaultCard) -> StepSource:
    src = card.source
    when = src.date.strftime("%b %Y") if src.date else None
    label = " · ".join(x for x in (src.author or src.doc, when) if x) or card.brand
    return StepSource(kind=src.type, label=label, audio_uri=src.audio_uri, doc=src.doc, page=src.page)


def start_repair(
    inp: StartRepairIn, job: RepairJob, cards: list[FaultCard]
) -> tuple[Started | StopRefer, RepairJob]:
    """`cards` are the fault cards named in `inp.card_ids`, in order. A step that hits a hard stop is never
    stored: the whole start returns STOP_REFER and the job is left as it was."""
    drafts: list[tuple[str, str, StepSource]] = []  # instruction, hazard, source
    for card in cards:
        if card.hazard == "refrigerant":
            return StopRefer(reason="refrigerant"), job
        drafts += [(text, card.hazard, _card_source(card)) for text in card.fix_steps]
    for proposed in inp.steps:
        hazard, stop = tag(proposed.summary_en, "none")
        if stop:
            return StopRefer(reason=stop), job
        drafts.append((proposed.instruction, hazard, GENERAL))
    steps = [RepairStep(n=n, instruction=i, hazard=h, source=s) for n, (i, h, s) in enumerate(drafts, 1)]
    job = job.model_copy(update={"steps": steps, "current_step": 0})
    return Started(of=len(steps), steps=[PlannedStep(n=s.n, hazard=s.hazard, source=s.source) for s in steps]), job


def next_step(job: RepairJob) -> tuple[StepOut | SafetyGateOut | RepairDone, RepairJob]:
    if job.current_step >= len(job.steps):
        return RepairDone(), job
    gate = open_gate(job)
    if gate:
        return SafetyGateOut(gate_id=gate, required_evidence=EVIDENCE[gate]), job
    # The only place a step's instruction leaves the server.
    step = job.steps[job.current_step]
    return StepOut(job_id=job.job_id, of=len(job.steps), step=step), job.model_copy(
        update={"current_step": job.current_step + 1}
    )


def confirm_safety(inp: ConfirmSafetyIn, job: RepairJob, check: GateCheck) -> tuple[ConfirmSafetyOut, RepairJob]:
    """`check` is Flash vision's reading of `inp.media_uri`. Words never open a gate; only a photo that passes here."""
    sure = check.passed and check.confidence >= MIN_GATE_CONFIDENCE
    if inp.gate_id == "G_CAP_DISCHARGE":
        passed = sure and check.reading_volts is not None and abs(check.reading_volts) <= MAX_DISCHARGED_VOLTS
        reason = None if passed else RETRY_DISCHARGE
    else:
        passed = sure
        reason = None if passed else (check.reason or RETRY_MAINS)
    gates = {**job.gates, inp.gate_id: "passed" if passed else "failed"}
    return ConfirmSafetyOut(gate_id=inp.gate_id, passed=passed, reason=reason), job.model_copy(update={"gates": gates})
