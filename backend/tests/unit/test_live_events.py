from google.adk.events import Event
from google.genai import types

from app.live_events import to_frames
from models.ws import Caption, Interrupted, ResumeHandle, TurnComplete


def ev(**fields):
    return Event(author="ustaad", **fields)


def said(who, text, partial):
    field = "input_transcription" if who == "user" else "output_transcription"
    return ev(partial=partial, **{field: types.Transcription(text=text, finished=not partial)})


def test_model_audio_becomes_a_binary_frame():
    audio = types.Part(inline_data=types.Blob(data=b"\x01\x02", mime_type="audio/pcm;rate=24000"))
    assert to_frames(ev(content=types.Content(role="model", parts=[audio])), {}) == [b"\x01\x02"]


def test_partial_captions_carry_the_text_so_far_and_the_final_replaces_them():
    partials = {}
    assert to_frames(said("ustaad", "Pehle ", True), partials) == [Caption(who="ustaad", text="Pehle ", final=False)]
    assert to_frames(said("ustaad", "MCB", True), partials) == [Caption(who="ustaad", text="Pehle MCB", final=False)]
    final = to_frames(said("ustaad", "Pehle MCB band karo", False), partials)
    assert final == [Caption(who="ustaad", text="Pehle MCB band karo", final=True)]
    assert to_frames(said("ustaad", "Ab", True), partials) == [Caption(who="ustaad", text="Ab", final=False)]


def test_user_speech_is_captioned_as_user():
    assert to_frames(said("user", "E6 aa raha hai", False), {}) == [
        Caption(who="user", text="E6 aa raha hai", final=True)
    ]


def test_interrupted_and_turn_complete():
    assert to_frames(ev(interrupted=True), {}) == [Interrupted()]
    assert to_frames(ev(turn_complete=True), {}) == [TurnComplete()]


def test_resume_handle_only_when_the_model_gives_one():
    update = types.LiveServerSessionResumptionUpdate(new_handle="h1", resumable=True)
    assert to_frames(ev(live_session_resumption_update=update), {}) == [ResumeHandle(handle="h1")]
    assert to_frames(ev(live_session_resumption_update=types.LiveServerSessionResumptionUpdate()), {}) == []


def test_tool_calls_and_text_parts_send_nothing_to_the_phone():
    call = types.Part(function_call=types.FunctionCall(name="x", args={}))
    assert to_frames(ev(content=types.Content(role="model", parts=[call, types.Part(text="thinking")])), {}) == []
