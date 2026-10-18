"""The agent's search_fault_cards tool: BLOCKING, and it runs the pure search against the card store."""

from google.genai import types

from agent.search_tools import search_tools
from models.fault_card import FaultCard
from tests.unit.fake_cards import FakeCardStore, embed


def test_search_fault_cards_is_blocking():
    (tool,) = search_tools(FakeCardStore(), embed)
    assert tool.name == "search_fault_cards"
    assert tool.behavior == types.Behavior.BLOCKING


async def test_the_tool_returns_the_matching_card_without_step_text():
    store = FakeCardStore()
    card = FaultCard(
        id="fc_e6", created_at="2026-10-16T00:00:00Z", brand="Voltas", error_code="E6", symptom="Test symptom",
        fix_steps=["Test step that must not leak"], hazard="HV", source={"type": "whatsapp_voice", "author": "Samyak"},
        confidence=0.9,
    )
    store.save(card, embed(["Voltas E6 Test symptom"], "RETRIEVAL_DOCUMENT")[0])
    (tool,) = search_tools(store, embed)
    out = await tool.run_async(args={"brand": "voltas", "error_code": "E6"}, tool_context=None)
    assert out["cards"][0]["card_id"] == "fc_e6"
    assert "must not leak" not in str(out)


async def test_a_failed_search_answers_unavailable_instead_of_ending_the_live_session(caplog):
    # ustaad-02's local T39 run (Oct 18): an embed ReadTimeout raised out of the tool, and ADK ended the Live session.
    caplog.set_level("DEBUG")

    def failing_embed(texts, task_type):
        raise TimeoutError("https://aiplatform.googleapis.com/...?key=SYNTHETIC_TOKEN timed out")

    (tool,) = search_tools(FakeCardStore(), failing_embed)
    out = await tool.run_async(args={"brand": "voltas", "error_code": "E6"}, tool_context=None)
    assert out["cards"] == [] and out["unavailable"] is True
    assert [r.getMessage() for r in caplog.records] == ["card search failed (TimeoutError)"]
    assert "SYNTHETIC_TOKEN" not in caplog.text
