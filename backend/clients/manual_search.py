"""The normalized boundary for Agent Search manual retrieval."""

import os
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


# Measured 3.2–3.8 s per real query (Oct 18); a hung call must not leave Ustaad silent.
SEARCH_TIMEOUT_S = 8.0


class DiscoverySearchService(Protocol):
    def search(self, request: object, timeout: float) -> object: ...


class DiscoveryEngineManualSearch:
    """Retrieves page-cited chunks of the brand's own manuals from the configured private data store."""

    def __init__(self, project: str, datastore: str, service: DiscoverySearchService | None = None) -> None:
        self._datastore = datastore
        self._project = project
        self._service = service or discoveryengine.SearchServiceClient()

    def search(self, query: str, brand: str, model: str | None) -> list[ManualSearchResult]:
        spec = discoveryengine.SearchRequest.ContentSearchSpec
        request = discoveryengine.SearchRequest(
            serving_config=(
                f"projects/{self._project}/locations/global/collections/default_collection/"
                f"dataStores/{self._datastore}/servingConfigs/default_serving_config"
            ),
            # Without the brand, "E6" ranks Daikin's and LG's code tables above Voltas's (measured Oct 18).
            query=" ".join(part for part in (brand, query, model) if part),
            page_size=5,
            # Chunks carry their page span, which the Standard edition returns (extractive answers need Enterprise).
            content_search_spec=spec(search_result_mode=spec.SearchResultMode.CHUNKS),
        )
        try:
            # Only the first page: iterating the pager would fetch further pages, one RPC each.
            results = next(
                iter(self._service.search(request=request, timeout=SEARCH_TIMEOUT_S).pages)
            ).results
            return [snippet for result in results if (snippet := _snippet(result, brand))]
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
    chunk = result.chunk
    # Manuals are stored as gs://…/manuals/<brand>-<name>.pdf; matching the prefix keeps another brand's code out.
    doc = PurePosixPath(chunk.document_metadata.uri).name
    if doc.split("-", 1)[0].casefold() != brand.casefold() or chunk.page_span.page_start <= 0:
        return None
    return ManualSearchResult(brand=brand, text=chunk.content, doc=doc, page=chunk.page_span.page_start)
