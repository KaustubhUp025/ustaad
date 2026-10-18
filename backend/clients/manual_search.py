"""The normalized boundary for Agent Search manual retrieval."""

import os
from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import PurePosixPath
from typing import Protocol

from google.cloud import discoveryengine_v1 as discoveryengine
from pydantic import BaseModel


class ManualSearchResult(BaseModel):
    brand: str
    text: str | None
    doc: str | None
    page: int | None


class ManualSearchUnavailable(Exception):
    pass


class ManualSearchClient(Protocol):
    def search(self, query: str, brand: str, model: str | None) -> list[ManualSearchResult]: ...


class UnavailableManualSearch:
    def search(self, query: str, brand: str, model: str | None) -> list[ManualSearchResult]:
        raise ManualSearchUnavailable


class DiscoverySearchService(Protocol):
    def search(self, request: object) -> Iterable[object]: ...


class DiscoveryEngineManualSearch:
    """Retrieves only page-cited extracts from the configured private data store."""

    def __init__(self, project: str, datastore: str, service: DiscoverySearchService | None = None) -> None:
        self._datastore = datastore
        self._project = project
        self._service = service or discoveryengine.SearchServiceClient()

    def search(self, query: str, brand: str, model: str | None) -> list[ManualSearchResult]:
        request = discoveryengine.SearchRequest(
            serving_config=(
                f"projects/{self._project}/locations/global/collections/default_collection/"
                f"dataStores/{self._datastore}/servingConfigs/default_serving_config"
            ),
            query=f"{query} {model}" if model else query,
            page_size=5,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                    max_extractive_answer_count=1
                )
            ),
        )
        try:
            return [snippet for result in self._service.search(request=request) if (snippet := _snippet(result, brand))]
        except Exception:  # noqa: BLE001 — service failures must remain safe at the tool boundary.
            raise ManualSearchUnavailable from None


@cache
def manual_search_client() -> ManualSearchClient:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    datastore = os.getenv("AGENT_SEARCH_DATASTORE")
    if not project or not datastore:
        return UnavailableManualSearch()
    try:
        return DiscoveryEngineManualSearch(project, datastore)
    except Exception:  # noqa: BLE001 — ADC setup is an unavailable search service, not a Live-session error.
        return UnavailableManualSearch()


def _snippet(result: object, brand: str) -> ManualSearchResult | None:
    document = getattr(result, "document", None)
    data = _mapping(getattr(document, "derived_struct_data", None))
    title = _text(data.get("title")) or _text(_mapping(getattr(document, "struct_data", None)).get("title"))
    source_name = _source_name(_text(data.get("link"))) or _source_name(_text(getattr(document, "name", None)))
    if not title and not source_name:
        return None
    source = " ".join(part for part in (title, source_name) if part)
    if brand.casefold() not in source.casefold():
        return None
    for candidate in _items(data.get("extractive_answers")):
        answer = _mapping(candidate)
        text = _text(answer.get("content"))
        page = _page(answer.get("pageNumber"))
        if text and page is not None:
            return ManualSearchResult(brand=brand, text=text, doc=title or source_name, page=page)
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _items(value: object) -> Iterable[object]:
    return value if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)) else ()


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _page(value: object) -> int | None:
    try:
        page = int(value) if value is not None else 0
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def _source_name(link: str | None) -> str | None:
    return PurePosixPath(link).name if link else None
