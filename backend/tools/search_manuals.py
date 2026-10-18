"""Maps normalized Agent Search results to the cited snippets the agent may use."""

from collections.abc import Callable

from clients.manual_search import ManualSearchResult
from models.tools import ManualSnippet, SearchManualsIn, SearchManualsOut

Search = Callable[[str, str, str | None], list[ManualSearchResult]]


def search_manuals(inp: SearchManualsIn, search: Search) -> SearchManualsOut:
    brand = inp.brand.strip().casefold()
    snippets = [
        ManualSnippet(text=result.text.strip(), doc=result.doc.strip(), page=result.page)
        for result in search(inp.query, inp.brand, inp.model)
        if result.brand.strip().casefold() == brand
        and result.text
        and result.text.strip()
        and result.doc
        and result.doc.strip()
        and result.page is not None
        and result.page > 0
    ]
    return SearchManualsOut(snippets=snippets)
