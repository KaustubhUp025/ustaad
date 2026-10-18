from google.adk.events import Event
from google.genai import types

from app.live_events import ahead, to_frames
from models.repair import RepairJob
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


def test_backstop_a_final_ustaad_caption_that_matches_a_stop_row_sends_safety_stop():
    frames = to_frames(said("ustaad", "Ab gas recharge karte hain", False), {})
    assert frames == [
        Caption(who="ustaad", text="Ab gas recharge karte hain", final=True),
        SafetyStop(reason="refrigerant", message="Stopped for safety"),
    ]


def test_backstop_a_gas_question_from_the_worker_gets_the_stop_screen():
    assert SafetyStop(reason="refrigerant", message="Stopped for safety") in to_frames(
        said("user", "Gas kaise bharun?", False), {}
    )


def test_backstop_waits_for_the_final_caption_and_ignores_hazard_rows():
    assert to_frames(said("ustaad", "Magnetron", True), {}) == [Caption(who="ustaad", text="Magnetron", final=False)]
    assert to_frames(said("ustaad", "PCB ke terminal dekho", False), {}) == [
        Caption(who="ustaad", text="PCB ke terminal dekho", final=True)
    ]


def test_backstop_leaves_power_on_diagnosis_talk_alone():
    # Power-on diagnosis happens in conversation before start_repair (SAFETY.md), so it is not a stop on speech.
    assert to_frames(said("ustaad", "Check karo supply aa rahi hai ya nahi", False), {}) == [
        Caption(who="ustaad", text="Check karo supply aa rahi hai ya nahi", final=True)
    ]


def _job(*instructions, current_step=0):
    steps = [
        {
            "n": n,
            "instruction": text,
            "hazard": "none",
            "source": {
                "kind": "general",
                "label": "General guidance",
                "audio_uri": None,
                "doc": None,
                "page": None,
            },
        }
        for n, text in enumerate(instructions, 1)
    ]
    return RepairJob(job_id="j_1", steps=steps, current_step=current_step)


Q1_STEP = "मशीन से जुड़ी पानी की सप्लाई का नल चेक करें कि वह खुला है या नहीं।"
Q1_SAID = "मेरे पास इस समस्या का कोई वेरिफाइड सोर्स नहीं है। हम कुछ सामान्य जाँच कर सकते हैं। क्या आप चेक कर सकते हैं कि मशीन से जुड़ी पानी की सप्लाई का नल खुला है या नहीं?"


def test_a_step_said_before_next_step_handed_it_out_is_ahead():
    assert ahead(Q1_SAID, _job(Q1_STEP)).n == 1


def test_a_step_already_handed_out_may_be_said():
    assert ahead(Q1_SAID, _job(Q1_STEP, current_step=1)) is None


def test_a_later_step_is_ahead_too():
    assert (
        ahead(
            "आउटडोर पीसीबी के टर्मिनल और वायरिंग देखो",
            _job("Outdoor unit ka PCB dikhao", "Outdoor PCB ke terminal aur wiring dekho", current_step=1),
        ).n
        == 2
    )


def test_a_job_with_no_steps_has_nothing_ahead():
    assert ahead(Q1_SAID, RepairJob(job_id="j_1")) is None


def test_backstop_catches_hindi_advice_to_open_a_geyser():
    # Q4 (Oct 18): said in conversation, a turn before start_repair stored anything.
    said = "कोई फॉल्ट कार्ड नहीं मिला। एक बार गीज़र का पैनल खोलकर थर्मोस्टेट का रीसेट बटन चेक करना पड़ेगा।"
    assert SafetyStop(reason="geyser_open", message="Stopped for safety") in to_frames(
        said_final("ustaad", said), {}
    )


def test_backstop_leaves_the_good_hindi_answers_alone():
    for said in (
        "LG फ्रिज के E1 एरर कोड का मतलब मेरे पास मौजूद रिकॉर्ड्स में नहीं है। क्या आप मुझे फ्रिज के मैनुअल का पेज या फिर वायरिंग का स्टीकर दिखा सकते हैं?",
        "बिना मॉडल नंबर या फोटो के, मैं आपको केवल सामान्य जानकारी दे सकता हूँ। क्या माइक्रोवेव चलते समय कोई असामान्य आवाज़ कर रहा है, या अंदर की लाइट जल रही है?",
        "सॉकेट में वोल्टेज चेक करने जैसा लाइव टेस्ट करने के लिए मैं आपको गाइड नहीं कर सकता क्योंकि इसमें बिजली का खतरा होता है।",
        "AC में गैस कम हो सकती है, पहले आउटडोर यूनिट का फैन देखिए।",
    ):
        assert not [f for f in to_frames(said_final("ustaad", said), {}) if isinstance(f, SafetyStop)], said


def test_backstop_catches_a_hindi_gas_question():
    assert SafetyStop(reason="refrigerant", message="Stopped for safety") in to_frames(
        said_final("user", "गैस कैसे भरूँ?"), {}
    )


def said_final(who, text):
    return said(who, text, False)
