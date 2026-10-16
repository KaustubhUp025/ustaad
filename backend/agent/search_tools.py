"""search_fault_cards as the Live agent calls it: the pure search in tools/search_fault_cards.py run against the
card store, off the event loop because the embedding call and the Firestore query block."""

import asyncio

from google.adk.tools import FunctionTool
from google.genai import types

from clients.firestore import CardStore
from models.repair import ApplianceType
from models.tools import SearchFaultCardsIn
from tools import search_fault_cards as search
from tools.search_fault_cards import Embed


def search_tools(cards: CardStore, embed: Embed) -> list[FunctionTool]:
    async def search_fault_cards(
        brand: str,
        model: str | None = None,
        error_code: str | None = None,
        symptom: str | None = None,
        appliance_type: ApplianceType | None = None,
    ) -> dict:
        """Finds fault cards the technicians' group recorded. Pass the brand, the error code exactly as shown, the
        symptom in his words, and the appliance type when known. Returns up to 5 cards, each with who said it and
        when (`citation`) and how many steps it has, but not the steps: pass the IDs of the cards you use to
        start_repair and get each step from next_step. An empty list means no card matched."""
        inp = SearchFaultCardsIn(
            brand=brand, model=model, error_code=error_code, symptom=symptom, appliance_type=appliance_type
        )
        out = await asyncio.to_thread(search.search_fault_cards, inp, embed, cards.nearest)
        return out.model_dump(mode="json")

    tool = FunctionTool(search_fault_cards)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
