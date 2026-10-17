from google.adk.events import Event
from google.genai import types

from app.live_events import to_frames
from models.ws import (
    Caption,
    GateResult,
    Interrupted,
    ResumeHandle,
    SafetyGate,
    SafetyStop,
    StepCard,
    TurnComplete,
)


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


def responded(name, response):
    part = types.Part(function_response=types.FunctionResponse(name=name, response=response))
    return ev(content=types.Content(role="user", parts=[part]))


SOURCE = {"kind": "general", "label": "General guidance", "audio_uri": None, "doc": None, "page": None}


def test_a_step_from_next_step_becomes_a_step_card():
    step = {"n": 2, "instruction": "Test step", "hazard": "HV", "source": SOURCE}
    out = {"status": "STEP", "job_id": "j_1", "of": 3, "step": step}
    assert to_frames(responded("next_step", out), {}) == [
        StepCard(job_id="j_1", n=2, of=3, instruction="Test step", hazard="HV", source=SOURCE)
    ]


def test_a_gate_from_next_step_or_the_callback_becomes_a_safety_gate():
    out = {"status": "SAFETY_GATE", "gate_id": "G_MAINS_OFF", "required_evidence": "MCB OFF photo"}
    for tool in ("next_step", "close_job"):
        [frame] = to_frames(responded(tool, out), {})
        assert isinstance(frame, SafetyGate)
        assert frame.gate_id == "G_MAINS_OFF" and frame.required_evidence == "MCB OFF photo"


def test_a_stop_becomes_a_safety_stop():
    [frame] = to_frames(responded("start_repair", {"status": "STOP_REFER", "reason": "refrigerant"}), {})
    assert isinstance(frame, SafetyStop) and frame.reason == "refrigerant"


def test_a_gate_check_becomes_a_gate_result():
    out = {"gate_id": "G_CAP_DISCHARGE", "passed": False, "reason": "Discharge it and measure again"}
    assert to_frames(responded("confirm_safety", out), {}) == [
        GateResult(gate_id="G_CAP_DISCHARGE", passed=False, reason="Discharge it and measure again")
    ]


def test_other_tool_results_send_no_frame():
    assert to_frames(responded("start_repair", {"status": "STARTED", "of": 2, "steps": []}), {}) == []
    assert to_frames(responded("next_step", {"status": "DONE"}), {}) == []


def test_a_step_card_in_an_english_session_carries_the_english_and_the_original():
    step = {"n": 1, "instruction": "Test ek", "instruction_en": "Test one", "hazard": "none", "source": SOURCE}
    out = {"status": "STEP", "job_id": "j_1", "of": 1, "step": step}
    (card,) = to_frames(responded("next_step", out), {}, "en")
    assert (card.instruction, card.instruction_translated) == ("Test ek", "Test one")
    (card,) = to_frames(responded("next_step", out), {}, "hi")
    assert (card.instruction, card.instruction_translated) == ("Test ek", None)
