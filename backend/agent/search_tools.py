"""search_fault_cards as the Live agent calls it: the pure search in tools/search_fault_cards.py run against the
card store, off the event loop because the embedding call and the Firestore query block."""

import asyncio
import logging

from google.adk.tools import FunctionTool
from google.genai import types

from clients.firestore import CardStore
from models.repair import ApplianceType
from models.tools import SearchFaultCardsIn, SearchFaultCardsOut
from tools import search_fault_cards as search
from tools.search_fault_cards import Embed

logger = logging.getLogger(__name__)


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
        start_repair and get each step from next_step. An empty list means no card matched. `unavailable` true means
        the search itself failed: tell him the records can't be reached right now, never guess what a code means, and
        search again on his next question."""
        inp = SearchFaultCardsIn(
            brand=brand, model=model, error_code=error_code, symptom=symptom, appliance_type=appliance_type
        )
        try:
            out = await asyncio.to_thread(search.search_fault_cards, inp, embed, cards.nearest)
        except Exception as exc:  # noqa: BLE001 — a tool that raises ends the whole Live session (ADK run_live)
            # Only the class: the error text can carry the request URL or a key.
            logger.error("card search failed (%s)", type(exc).__name__)
            out = SearchFaultCardsOut(cards=[], unavailable=True)
        return out.model_dump(mode="json")

    tool = FunctionTool(search_fault_cards)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
