"""set_reply_language as the Live agent calls it (agent/language_tools.py): the reply language is the job's until he
asks for another, and the switch reaches the tools, the notes and the phone's cards (phone test, Oct 18)."""

from types import SimpleNamespace

from agent.language_tools import language_tools
from agent.media_tools import MediaDesk


def setup():
    desk = MediaDesk("j_1", "media")
    desk.lang = "hi"
    state = {"job_id": "j_1", "lang": "hi", "language_name": "Hindi, written in Devanagari script"}
    return desk, SimpleNamespace(state=state), language_tools(desk)[0]


def test_switching_sets_the_language_for_the_tools_and_the_phone():
    desk, context, tool = setup()
    out = tool.func(context, lang="en")
    assert out == {"status": "SET", "language": "English"}
    assert (context.state["lang"], context.state["language_name"], desk.lang) == ("en", "English", "en")


def test_a_language_ustaad_does_not_speak_changes_nothing():
    desk, context, tool = setup()
    out = tool.func(context, lang="fr")
    assert out["status"] == "UNSUPPORTED"
    assert (context.state["lang"], desk.lang) == ("hi", "hi")


def test_the_instruction_pins_the_reply_language_and_switches_only_through_the_tool():
    from agent.ustaad import INSTRUCTION

    text = " ".join(INSTRUCTION.split())
    assert "Always reply in {language_name?}" in text
    assert "`set_reply_language`" in text
    assert "language he last spoke" not in text and "latest words" not in text
