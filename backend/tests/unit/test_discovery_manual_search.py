from pathlib import Path
from types import SimpleNamespace

import pytest
from google.cloud import discoveryengine_v1 as discoveryengine

from clients.manual_search import (
    SEARCH_TIMEOUT_S,
    DiscoveryEngineManualSearch,
    ManualSearchResult,
    ManualSearchUnavailable,
    UnavailableManualSearch,
    manual_search_client,
)


class FakeSearchService:
    def __init__(self, results: list[object] | None = None, error: Exception | None = None):
        self.results = results or []
        self.error = error
        self.requests: list[object] = []
        self.timeouts: list[float] = []

    def search(self, request: object, timeout: float) -> object:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.error:
            raise self.error
        # A pager: iterating `pages` would fetch more over RPC; the adapter must read only the first.
        return SimpleNamespace(pages=iter([SimpleNamespace(results=self.results), None]))


def result(uri: str, content: str, page_start: int | None) -> object:
    return SimpleNamespace(
        chunk=SimpleNamespace(
            content=content,
            document_metadata=SimpleNamespace(uri=uri, title="untitled"),
            page_span=SimpleNamespace(page_start=page_start or 0, page_end=page_start or 0),
        )
    )


VOLTAS = "gs://ustaad101-media/manuals/voltas-inverter-series.pdf"
# Recorded Oct 18 from ustaad-manuals-layout (layout parser, chunks) for the query "Voltas E6".
RECORDED = Path(__file__).parents[3] / "seed/fixtures/agent_search/voltas_e6.json"


def test_search_asks_the_global_datastore_for_chunks_with_a_timeout():
    service = FakeSearchService([result(VOLTAS, "Cited E6 answer", 12)])
    client = DiscoveryEngineManualSearch("ustaad101", "ustaad-manuals_123", service)

    assert client.search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Cited E6 answer", doc="voltas-inverter-series.pdf", page=12)
    ]
    request = service.requests[0]
    assert request.serving_config == (
        "projects/ustaad101/locations/global/collections/default_collection/"
        "dataStores/ustaad-manuals_123/servingConfigs/default_serving_config"
    )
    assert (
        request.content_search_spec.search_result_mode == request.content_search_spec.SearchResultMode.CHUNKS
    )
    assert service.timeouts == [SEARCH_TIMEOUT_S]


def test_the_brand_leads_the_query_so_its_own_manual_ranks_first():
    service = FakeSearchService()
    DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", "183V CZX")

    assert service.requests[0].query == "Voltas E6 183V CZX"


def test_a_recorded_response_gives_the_voltas_error_table_page():
    page = discoveryengine.SearchResponse.from_json(RECORDED.read_text(), ignore_unknown_fields=True)
    service = FakeSearchService(list(page.results))

    first = DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", None)[0]

    assert (first.doc, first.page) == ("voltas-inverter-series.pdf", 32)
    assert "E6 Indoor and outdoor machine communication fault" in first.text


def test_search_keeps_only_the_brands_own_manual():
    service = FakeSearchService(
        [
            result("gs://ustaad101-media/manuals/lg-MFL41161601.pdf", "Other brand", 4),
            result("gs://ustaad101-media/manuals/daikin-SiUS091133.pdf", "E6 Compressor lock", 116),
            result(VOLTAS, "Voltas citation", 5),
        ]
    )

    assert DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Voltas citation", doc="voltas-inverter-series.pdf", page=5)
    ]


def test_a_brand_inside_another_filename_does_not_match():
    service = FakeSearchService([result("gs://ustaad101-media/manuals/daikin-glgx.pdf", "Not LG", 3)])

    assert DiscoveryEngineManualSearch("ustaad101", "store", service).search("CH05", "LG", None) == []


def test_search_drops_chunks_without_a_page():
    service = FakeSearchService([result(VOLTAS, "No page", None), result(VOLTAS, "Good page", 9)])

    assert DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Good page", doc="voltas-inverter-series.pdf", page=9)
    ]


def test_search_returns_empty_results_unchanged():
    assert (
        DiscoveryEngineManualSearch("ustaad101", "store", FakeSearchService()).search("E6", "Voltas", None)
        == []
    )


def test_missing_configuration_preserves_the_offline_unavailable_client(monkeypatch):
    monkeypatch.delenv("AGENT_SEARCH_DATASTORE", raising=False)
    manual_search_client.cache_clear()

    assert isinstance(manual_search_client(), UnavailableManualSearch)

    manual_search_client.cache_clear()


def test_search_hides_service_failure_details():
    secret = "synthetic-discovery-request-id"
    client = DiscoveryEngineManualSearch("ustaad101", "store", FakeSearchService(error=RuntimeError(secret)))

    with pytest.raises(ManualSearchUnavailable, match="^$"):
        client.search("E6", "Voltas", None)
