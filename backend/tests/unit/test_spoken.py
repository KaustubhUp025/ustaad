"""Does a caption say a stored step? Captions and steps from the Oct 18 Hindi check and the G2 fixture."""

from tools.spoken import says, words

# Q1 washing machine (Oct 18): the step start_repair stored, and what Ustaad then said while the mains gate was open.
STORED = "मशीन से जुड़ी पानी की सप्लाई का नल चेक करें कि वह खुला है या नहीं।"
SAID = "क्या आप चेक कर सकते हैं कि मशीन से जुड़ी पानी की सप्लाई का नल खुला है या नहीं?"


def test_a_caption_that_says_the_stored_step_matches():
    assert says(words(SAID), words(STORED))


def test_the_first_words_of_the_step_are_enough():
    assert says(words("क्या आप चेक कर सकते हैं कि मशीन से जुड़ी पानी की सप्लाई"), words(STORED))


def test_hindi_speech_matches_a_hinglish_card_step():
    # G2 fixture step (Hinglish) spoken in Devanagari.
    assert says(
        words("आउटडोर पीसीबी के टर्मिनल और वायरिंग देखो"), words("Outdoor PCB ke terminal aur wiring dekho")
    )


def test_english_speech_matches_the_steps_english():
    assert says(
        words("Now look at the outdoor PCB terminals and the wiring"),
        words("Check the outdoor PCB terminals and wiring"),
    )


def test_a_question_about_the_appliance_does_not_match():
    # Q2 fridge and Q5 microwave answers (Oct 18): ordinary talk, not the stored step.
    assert not says(words("LG फ्रिज के E1 एरर कोड का मतलब मेरे पास मौजूद रिकॉर्ड्स में नहीं है।"), words(STORED))
    assert not says(
        words("क्या माइक्रोवेव चलते समय कोई असामान्य आवाज़ कर रहा है, या अंदर की लाइट जल रही है?"), words(STORED)
    )


def test_the_gate_instruction_does_not_match_the_step():
    assert not says(words("कृपया मशीन का पावर प्लग निकाल दें और उसकी फोटो भेजें।"), words(STORED))
