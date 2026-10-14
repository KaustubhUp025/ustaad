"""Which safety gate, if any, stands before a job's next step (docs/SAFETY.md). Pure: the tools and the
before_tool_callback both decide through this, each reading the job for itself."""

from models.repair import GateId, Hazard, RepairJob, RepairStep

HAZARD_GATES: dict[Hazard, tuple[GateId, ...]] = {
    "none": (),
    "HV": ("G_MAINS_OFF",),
    "capacitor": ("G_MAINS_OFF", "G_CAP_DISCHARGE"),
    "refrigerant": (),  # never stored: start_repair stops it
}
EVIDENCE: dict[GateId, str] = {
    "G_MAINS_OFF": "Photo of the MCB or isolator in the OFF position, or of the unit's plug pulled out",
    "G_CAP_DISCHARGE": "Photo of the multimeter display across the capacitor terminals",
}
# Flash vision questions (BUILD-GUIDE §7.7). For the capacitor the model only reads the meter; code decides.
QUESTIONS: dict[GateId, str] = {
    "G_MAINS_OFF": (
        "Is an MCB or isolator visibly in the OFF position in this photo, or is the unit's plug visibly pulled out "
        "of the socket? passed is true only if you can clearly see one of these. If unsure, passed is false. "
        "reason: one short sentence on what you see. confidence: 0 to 1."
    ),
    "G_CAP_DISCHARGE": (
        "This photo should show a multimeter display measuring across a capacitor's terminals. passed is true "
        "only if the display is clearly readable and set to DC volts. reading_volts: the number on the display, "
        "or null if you cannot read it. Do not guess digits. reason: one short sentence on what you see. "
        "confidence: 0 to 1."
    ),
}


def required_gates(job: RepairJob, step: RepairStep) -> tuple[GateId, ...]:
    gates = HAZARD_GATES[step.hazard]
    # Default gate (SAFETY.md): with no card or manual behind the job, mains goes off before the first step.
    if all(s.source.kind == "general" for s in job.steps) and "G_MAINS_OFF" not in gates:
        return ("G_MAINS_OFF", *gates)
    return gates


def open_gate(job: RepairJob) -> GateId | None:
    """The first gate the job's next step needs that has not passed; None when nothing is waiting on a gate."""
    if job.current_step >= len(job.steps):
        return None
    step = job.steps[job.current_step]
    return next((g for g in required_gates(job, step) if job.gates[g] != "passed"), None)
