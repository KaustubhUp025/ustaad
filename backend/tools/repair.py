"""The repair tools (SPEC §6, docs/SAFETY.md): start_repair stores a job's steps, next_step hands them out one at
a time behind their gates, confirm_safety judges a gate photo. Pure: each takes the job and returns its answer
and the updated job; loading, saving and the vision call are the caller's."""

from models.fault_card import FaultCard
from models.repair import RepairJob, RepairStep, StepSource
from models.tools import (
    ConfirmSafetyIn,
    ConfirmSafetyOut,
    GateCheck,
    ManualPage,
    NothingToPark,
    Parked,
    ParkedPlan,
    PlannedStep,
    RepairDone,
    SafetyGateOut,
    Started,
    StartRepairIn,
    StepOut,
    StopRefer,
)
from models.ws import StepCard
from tools.gates import EVIDENCE, open_gate
from tools.hazard_tagger import needs_power_on, tag

GENERAL = StepSource(kind="general", label="General guidance", audio_uri=None, doc=None, page=None)
MANUAL_PHOTO = StepSource(kind="manual_photo", label="Photo of manual", audio_uri=None, doc=None, page=None)
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
    inp: StartRepairIn, job: RepairJob, cards: list[FaultCard], page: ManualPage | None = None
) -> tuple[Started | StopRefer, RepairJob]:
    """`cards` are the fault cards named in `inp.card_ids`, in order; `page` is the manual page named by
    `inp.manual_request_id`. A step that hits a hard stop is never stored: the whole start returns STOP_REFER and
    the job is left as it was."""
    drafts: list[tuple[str, str | None, str, StepSource]] = []  # instruction, its English, hazard, source
    for card in cards:
        if card.hazard == "refrigerant":
            return StopRefer(reason="refrigerant"), job
        english = card.fix_steps_en or [None] * len(card.fix_steps)
        drafts += [(t, e, card.hazard, _card_source(card)) for t, e in zip(card.fix_steps, english, strict=True)]
    # A page's printed steps take the same tagging, gates and stops as proposed ones.
    sourced = [(p, GENERAL) for p in inp.steps] + [(p, MANUAL_PHOTO) for p in (page.steps if page else [])]
    for proposed, source in sourced:
        hazard, stop = tag(proposed.summary_en, "none")
        if stop:
            return StopRefer(reason=stop), job
        if source.kind == "general" and needs_power_on(proposed.summary_en):
            return StopRefer(reason="power_on"), job
        drafts.append((proposed.instruction, proposed.summary_en, hazard, source))
    steps = [
        RepairStep(n=n, instruction=i, instruction_en=e, hazard=h, source=s) for n, (i, e, h, s) in enumerate(drafts, 1)
    ]
    # A new plan starts with every gate open: power may have been switched back on since the last plan. The job's
    # photos stay: a side finding logged before a side plan is not lost (S7).
    job = RepairJob(job_id=job.job_id, steps=steps, media=job.media)
    return Started(of=len(steps), steps=[PlannedStep(n=s.n, hazard=s.hazard, source=s.source) for s in steps]), job


def next_step(job: RepairJob) -> tuple[StepOut | SafetyGateOut | RepairDone, RepairJob]:
    if job.current_step >= len(job.steps):
        return RepairDone(), job
    gate = open_gate(job)
    if gate:
        return SafetyGateOut(gate_id=gate, required_evidence=EVIDENCE[gate]), job
    # The only place a step's instruction leaves the server.
    step = job.steps[job.current_step]
    out = StepOut(job_id=job.job_id, of=len(job.steps), step=step, translation_lang=job.translation_lang)
    return out, job.model_copy(
        update={"current_step": job.current_step + 1}
    )


def park(job: RepairJob, issue: str) -> tuple[Parked | NothingToPark, ParkedPlan | None]:
    """The main repair at the step he is on, kept while a side issue is dealt with now (S7)."""
    if job.current_step == 0:
        return NothingToPark(), None
    plan = ParkedPlan(steps=job.steps, current_step=job.current_step, translation_lang=job.translation_lang, issue=issue)
    return Parked(n=job.current_step, of=len(job.steps)), plan


def resume(job: RepairJob, parked: ParkedPlan | None) -> tuple[StepOut | SafetyGateOut | RepairDone, RepairJob]:
    """The step he was on, again, through next_step and its gates. A parked plan comes back with every gate open:
    the side work was a plan of its own (SAFETY.md), and power may be back on."""
    if parked is not None:
        job = RepairJob(
            job_id=job.job_id,
            steps=parked.steps,
            current_step=parked.current_step,
            translation_lang=parked.translation_lang,
            media=job.media,
        )
    return next_step(job.model_copy(update={"current_step": max(job.current_step - 1, 0)}))


def step_card(out: StepOut, lang: str) -> StepCard:
    """The phone's card for a handed-out step: the original words, plus the English for an English session or the
    stored translation when it is in the session's language (a Telugu translation never shows in a Tamil session).
    Hindi shows the original."""
    step = out.step
    if lang == "en":
        translated = step.instruction_en
    else:
        translated = step.instruction_translated if out.translation_lang == lang else None
    shown = step.model_dump(exclude={"instruction_en", "instruction_translated"})
    return StepCard(job_id=out.job_id, of=out.of, **shown, instruction_translated=translated)


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
