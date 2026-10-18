import pytest
from google.genai import types
from pydantic import ValidationError

from agent.manual_tools import manual_tools
from clients.manual_search import ManualSearchResult, ManualSearchUnavailable
from models.tools import ManualSnippet


class FakeManualSearch:
    def __init__(self, results: list[ManualSearchResult] | None = None, error: Exception | None = None):
        self.results = results or []
        self.error = error
        self.calls: list[tuple[str, str, str | None]] = []

    def search(self, query: str, brand: str, model: str | None) -> list[ManualSearchResult]:
        self.calls.append((query, brand, model))
        if self.error:
            raise self.error
        return self.results


def test_search_manuals_is_blocking():
    (tool,) = manual_tools(FakeManualSearch())
    assert (tool.name, tool.behavior) == ("search_manuals", types.Behavior.BLOCKING)


def test_manual_snippet_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ManualSnippet(text="Recorded manual snippet", doc="Voltas manual", page=30, extra="not allowed")


async def test_search_manuals_returns_only_page_cited_snippets_for_the_asked_brand():
    client = FakeManualSearch(
        [
            ManualSearchResult(brand="Voltas", text="Recorded manual snippet", doc="Voltas manual", page=30),
            ManualSearchResult(brand="LG", text="Other brand", doc="LG manual", page=4),
            ManualSearchResult(brand="Voltas", text="Missing page", doc="Voltas manual", page=None),
        ]
    )
    (tool,) = manual_tools(client)

    out = await tool.run_async(args={"query": "E6", "brand": "voltas", "model": "183V"}, tool_context=None)

    assert out == {"snippets": [{"text": "Recorded manual snippet", "doc": "Voltas manual", "page": 30}]}
    assert client.calls == [("E6", "voltas", "183V")]


async def test_search_manuals_returns_no_results_when_the_store_has_no_match():
    (tool,) = manual_tools(FakeManualSearch())

    assert await tool.run_async(args={"query": "unknown", "brand": "Voltas"}, tool_context=None) == {"snippets": []}


async def test_unavailable_store_returns_no_results_without_leaking_its_error(caplog):
    secret = "synthetic-agent-search-token"
    (tool,) = manual_tools(FakeManualSearch(error=ManualSearchUnavailable(secret)))

    out = await tool.run_async(args={"query": "E6", "brand": "Voltas"}, tool_context=None)

    assert out == {"snippets": []}
    assert secret not in str(out)
    assert secret not in caplog.text
