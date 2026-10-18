from types import SimpleNamespace

import pytest

from clients.manual_search import (
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

    def search(self, request: object) -> list[object]:
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.results


def result(title: str, source: str, answers: list[dict[str, str]]) -> object:
    return SimpleNamespace(
        document=SimpleNamespace(
            derived_struct_data={"title": title, "link": source, "extractive_answers": answers}
        )
    )


def test_search_uses_global_datastore_and_returns_only_valid_cited_answers():
    service = FakeSearchService(
        [
            result(
                "Voltas Inverter Series",
                "gs://ustaad101-media/manuals/voltas-inverter-series.pdf",
                [{"content": "Cited E6 answer", "pageNumber": "12"}],
            )
        ]
    )
    client = DiscoveryEngineManualSearch("ustaad101", "ustaad-manuals_123", service)

    assert client.search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Cited E6 answer", doc="Voltas Inverter Series", page=12)
    ]
    request = service.requests[0]
    assert request.serving_config == (
        "projects/ustaad101/locations/global/collections/default_collection/"
        "dataStores/ustaad-manuals_123/servingConfigs/default_serving_config"
    )


def test_search_filters_results_from_another_brand():
    service = FakeSearchService(
        [
            result(
                "LG Service Manual",
                "gs://ustaad101-media/manuals/lg-MFL41161601.pdf",
                [{"content": "Other brand", "pageNumber": "4"}],
            ),
            result(
                "Voltas Inverter Series",
                "gs://ustaad101-media/manuals/voltas-inverter-series.pdf",
                [{"content": "Voltas citation", "pageNumber": "5"}],
            ),
        ]
    )

    assert DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Voltas citation", doc="Voltas Inverter Series", page=5)
    ]


def test_search_drops_answers_without_a_positive_page_number():
    service = FakeSearchService(
        [
            result(
                "Voltas Inverter Series",
                "gs://ustaad101-media/manuals/voltas-inverter-series.pdf",
                [
                    {"content": "No page"},
                    {"content": "Bad page", "pageNumber": "zero"},
                    {"content": "Zero page", "pageNumber": "0"},
                    {"content": "Good page", "pageNumber": "9"},
                ],
            )
        ]
    )

    assert DiscoveryEngineManualSearch("ustaad101", "store", service).search("E6", "Voltas", None) == [
        ManualSearchResult(brand="Voltas", text="Good page", doc="Voltas Inverter Series", page=9)
    ]


def test_search_returns_empty_results_unchanged():
    assert DiscoveryEngineManualSearch("ustaad101", "store", FakeSearchService()).search("E6", "Voltas", None) == []


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
