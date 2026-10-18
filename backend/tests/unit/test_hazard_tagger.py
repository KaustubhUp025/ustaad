import pytest

from tools.hazard_tagger import RULES, speech_stop, tag

# Test strings only: they name a part so a rule can match, and carry no repair guidance.
CASES = [
    ("Test step with refrigerant gas", "refrigerant"),
    ("Test step near the magnetron", "microwave_hv"),
    ("Test step with the microwave cover off", "microwave_hv"),
    ("Test step at the picture tube", "crt"),
    ("Test step inside the geyser", "geyser_open"),
    ("Test step at the capacitor", "capacitor"),
    ("Test step at the PCB terminals", "HV"),
]


@pytest.mark.parametrize(("summary", "outcome"), CASES)
def test_each_rules_row_gives_its_outcome(summary, outcome):
    hazard, stop = tag(summary, "none")
    assert outcome in (hazard, stop)


def test_every_rules_row_has_a_case():
    assert {outcome for outcome, _ in RULES} == {outcome for _, outcome in CASES}


def test_a_capacitor_mention_is_tagged_capacitor():
    assert tag("Test step: capacitors on the outdoor unit", "none") == ("capacitor", None)


def test_a_stop_row_wins_over_a_hazard_row():
    assert tag("Test step at the microwave high voltage capacitor", "none")[1] == "microwave_hv"


def test_hazard_is_never_lowered():
    assert tag("Test step at the air filter", "capacitor") == ("capacitor", None)
    assert tag("Test step at the PCB", "capacitor") == ("capacitor", None)


def test_a_refrigerant_hazard_is_a_stop():
    assert tag("Test step at the air filter", "refrigerant")[1] == "refrigerant"


def test_plain_text_gets_no_hazard():
    assert tag("Test step at the air filter", "none") == ("none", None)


def test_a_word_inside_another_word_does_not_match():
    assert tag("Test step at the door gasket", "none") == ("none", None)


@pytest.mark.parametrize(
    ("said", "reason"),
    [
        ("गीज़र का पैनल खोलकर थर्मोस्टेट देखिए", "geyser_open"),
        ("गैस भरनी पड़ेगी", "refrigerant"),
        ("माइक्रोवेव का कैपेसिटर डिस्चार्ज करो", "microwave_hv"),
        ("मैग्नेट्रॉन बदलना होगा", "microwave_hv"),
        ("पिक्चर ट्यूब में करंट रहता है", "crt"),
        ("గీజర్ ప్యానెల్ తెరిచి చూడండి", "geyser_open"),
        ("கீசரைத் திறந்து பாருங்கள்", "geyser_open"),
        ("গিজার খুলে দেখুন", "geyser_open"),
        ("గ్యాస్ నింపాలి", "refrigerant"),
        ("கேஸ் நிரப்ப வேண்டும்", "refrigerant"),
        ("গ্যাস ভরতে হবে", "refrigerant"),
        ("Recharge the gas", "refrigerant"),
    ],
)
def test_speech_in_any_script_hits_its_stop_row(said, reason):
    assert speech_stop(said) == reason


@pytest.mark.parametrize(
    "said",
    [
        "AC में गैस कम हो सकती है",
        "माइक्रोवेव के अंदर की लाइट जल रही है?",
        "गीज़र में इंडिकेटर लाइट जल रही है?",
        "पावर सप्लाई चेक करो",
    ],
)
def test_a_mention_in_conversation_is_not_a_stop(said):
    assert speech_stop(said) is None
