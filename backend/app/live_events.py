"""Turns one ADK Live event into what the phone gets: audio bytes and v1 frames (ws-events.md)."""

from typing import Any

from google.adk.events import Event

from models.repair import GateId, RepairJob, RepairStep
from models.tools import StepOut
from models.ws import (
    Caption,
    Frame,
    GateResult,
    Interrupted,
    ResumeHandle,
    SafetyGate,
    SafetyStop,
    TurnComplete,
)
from tools import spoken
from tools.hazard_tagger import hands_on, repair_talk, speech_power_on, speech_stop, without_gate_words
from tools.repair import step_card

# Sent to Ustaad when the server cut him off for saying a step next_step had not handed out.
AHEAD_NOTE = (
    "[The app stopped you: you began saying a repair step that next_step has not handed out. Never say a step "
    "before next_step returns it. Call next_step now; if it returns SAFETY_GATE, tell him only what to switch off "
    "and photograph.]"
)


# Sent to Ustaad when his turn was held back because a gate is open and he talked about the repair.
GATE_NOTE = (
    "[The app did not play your last answer: a safety gate is open. Until its photo passes, talk only about the gate: "
    "what to switch off and what to photograph. Answer his questions, but give no check, part or step.]"
)


def _backstop(caption: str) -> SafetyStop | None:
    """Backstop on speech, not a gate (SAFETY.md): it fires after the words have begun, so it only catches what the
    tool and the gates did not. Both speakers count, so a gas question from the worker also gets the stop screen."""
    stop = speech_stop(caption)
    return SafetyStop(reason=stop, message="Stopped for safety") if stop else None


def ahead(said: str, job: RepairJob) -> RepairStep | None:
    """The stored step this caption says that next_step has not handed out yet, if any (SAFETY.md, speech guard).
    A step is compared in every form it is stored in: as written, its English and its translation."""
    heard = spoken.words(said)
    for step in job.steps[job.current_step :]:
        forms = (step.instruction, step.instruction_en, step.instruction_translated)
        if any(form and spoken.says(heard, spoken.words(form)) for form in forms):
            return step
    return None


def releasable(said: str, job: RepairJob, gate: GateId) -> bool:
    """Whether a turn Ustaad finished while `gate` was open may be played: gate talk and questions are; repair talk,
    power-on talk, a stored step or a stop row are not. The server drops the turn on anything else, an error included."""
    talk = without_gate_words(said, gate)
    return not (speech_stop(said) or ahead(said, job) or repair_talk(talk) or speech_power_on(talk))


def power_on_stop(said: str, job: RepairJob) -> bool:
    """Spoken power-on advice that gets the `power_on` stop (SAFETY.md): on a general job any power-on check, as for
    its steps; before start_repair only power on with hands-on inspection (a torch, a part, an opened cover), since
    power-on diagnosis talk belongs there; on a card or manual job none, its steps may need the power on."""
    if not job.steps:
        return speech_power_on(said) and hands_on(said)
    return all(step.source.kind == "general" for step in job.steps) and speech_power_on(said)


def _tool_frame(name: str, result: dict[str, Any], lang: str) -> Frame | None:
    """The repair screens follow the tools' results, including a result the gate callback put in a tool's place.
    The phone shows its own text for each gate and stop, so `message` is only a short English label."""
    status = result.get("status")
    if status == "STEP":
        return step_card(StepOut.model_validate(result), lang)
    if status == "SAFETY_GATE":
        return SafetyGate(
            gate_id=result["gate_id"], message="Safety check first", required_evidence=result["required_evidence"]
        )
    if status == "STOP_REFER":
        return SafetyStop(reason=result["reason"], message="Stopped for safety")
    if name == "confirm_safety":
        return GateResult(**result)
    return None


def to_frames(event: Event, partials: dict[str, str], lang: str = "hi") -> list[Frame | bytes]:
    """`partials` holds each speaker's caption so far: ADK sends partial transcripts as fragments,
    while the contract wants every partial caption to replace the one before it."""
    out: list[Frame | bytes] = []
    for part in (event.content.parts or []) if event.content else []:
        if part.inline_data and part.inline_data.data:
            out.append(part.inline_data.data)
        if part.function_response and part.function_response.response is not None:
            frame = _tool_frame(part.function_response.name, part.function_response.response, lang)
            if frame:
                out.append(frame)
    for who, said in (("user", event.input_transcription), ("ustaad", event.output_transcription)):
        if said and said.text:
            if event.partial:
                partials[who] = partials.get(who, "") + said.text
                out.append(Caption(who=who, text=partials[who], final=False))
            else:
                partials.pop(who, None)
                out.append(Caption(who=who, text=said.text, final=True))
                stop = _backstop(said.text)
                if stop:
                    out.append(stop)
    if event.interrupted:
        out.append(Interrupted())
    if event.turn_complete:
        out.append(TurnComplete())
    update = event.live_session_resumption_update
    if update and update.new_handle:
        out.append(ResumeHandle(handle=update.new_handle))
    return out
