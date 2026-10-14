"""Turns one ADK Live event into what the phone gets: audio bytes and v1 frames (ws-events.md)."""

from typing import Any

from google.adk.events import Event

from models.ws import (
    Caption,
    Frame,
    GateResult,
    Interrupted,
    ResumeHandle,
    SafetyGate,
    SafetyStop,
    StepCard,
    TurnComplete,
)


def _tool_frame(name: str, result: dict[str, Any]) -> Frame | None:
    """The repair screens follow the tools' results, including a result the gate callback put in a tool's place.
    The phone shows its own text for each gate and stop, so `message` is only a short English label."""
    status = result.get("status")
    if status == "STEP":
        step = result["step"]
        return StepCard(job_id=result["job_id"], of=result["of"], **step)
    if status == "SAFETY_GATE":
        return SafetyGate(
            gate_id=result["gate_id"], message="Safety check first", required_evidence=result["required_evidence"]
        )
    if status == "STOP_REFER":
        return SafetyStop(reason=result["reason"], message="Stopped for safety")
    if name == "confirm_safety":
        return GateResult(**result)
    return None


def to_frames(event: Event, partials: dict[str, str]) -> list[Frame | bytes]:
    """`partials` holds each speaker's caption so far: ADK sends partial transcripts as fragments,
    while the contract wants every partial caption to replace the one before it."""
    out: list[Frame | bytes] = []
    for part in (event.content.parts or []) if event.content else []:
        if part.inline_data and part.inline_data.data:
            out.append(part.inline_data.data)
        if part.function_response and part.function_response.response is not None:
            frame = _tool_frame(part.function_response.name, part.function_response.response)
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
    if event.interrupted:
        out.append(Interrupted())
    if event.turn_complete:
        out.append(TurnComplete())
    update = event.live_session_resumption_update
    if update and update.new_handle:
        out.append(ResumeHandle(handle=update.new_handle))
    return out
