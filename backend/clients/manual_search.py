"""The normalized boundary for Agent Search manual retrieval."""

from typing import Protocol

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
