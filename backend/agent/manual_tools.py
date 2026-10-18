"""The blocking, cited-manual search tool used by the Live agent."""

import asyncio

from google.adk.tools import FunctionTool
from google.genai import types

from clients.manual_search import ManualSearchClient, ManualSearchUnavailable
from models.tools import SearchManualsIn, SearchManualsOut
from tools import search_manuals as search


def manual_tools(client: ManualSearchClient) -> list[FunctionTool]:
    async def search_manuals(query: str, brand: str, model: str | None = None) -> dict:
        """Finds page-cited text in the identified brand's service manuals. Call after search_fault_cards has no
        answer, with the worker's question, brand and model when known. Cite the returned document and page aloud;
        do not make up a manual answer when snippets is empty."""
        inp = SearchManualsIn(query=query, brand=brand, model=model)
        try:
            out = await asyncio.to_thread(search.search_manuals, inp, client.search)
        except ManualSearchUnavailable:
            out = SearchManualsOut(snippets=[])
        return out.model_dump(mode="json")

    tool = FunctionTool(search_manuals)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
