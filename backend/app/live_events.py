"""Turns one ADK Live event into what the phone gets: audio bytes and v1 frames (ws-events.md)."""

from google.adk.events import Event

from models.ws import Caption, Frame, Interrupted, ResumeHandle, TurnComplete


def to_frames(event: Event, partials: dict[str, str]) -> list[Frame | bytes]:
    """`partials` holds each speaker's caption so far: ADK sends partial transcripts as fragments,
    while the contract wants every partial caption to replace the one before it."""
    out: list[Frame | bytes] = []
    for part in (event.content.parts or []) if event.content else []:
        if part.inline_data and part.inline_data.data:
            out.append(part.inline_data.data)
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
