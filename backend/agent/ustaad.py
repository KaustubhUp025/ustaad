"""The one Ustaad agent (SPEC §6). Tools are added by their own tasks."""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.models import Gemini

from agent.callbacks import gate_guard
from agent.close_tools import close_tools
from agent.identify_tools import identify_tools
from agent.inventory_tools import inventory_tools
from agent.media_tools import MediaDesk, ReadPhoto, media_tools
from agent.quote_tools import quote_tools
from agent.repair_tools import repair_tools
from agent.search_tools import search_tools
from clients.firestore import CardStore, InventoryStore, JobStore, QuoteStore
from clients.gemini import embed
from clients.telegram import TelegramBot

INSTRUCTION = (Path(__file__).parent / "instruction.md").read_text(encoding="utf-8")


def build_ustaad(
    model: str,
    location: str,
    jobs: JobStore,
    cards: CardStore,
    inventory: InventoryStore,
    quotes: QuoteStore,
    bot: TelegramBot,
    desk: MediaDesk,
    read_photo: ReadPhoto,
) -> Agent:
    # The Live model is served from a different region than the rest of the app (DECISIONS, Oct 13).
    return Agent(
        name="ustaad",
        model=Gemini(model=model, client_kwargs={"location": location}),
        instruction=INSTRUCTION,
        tools=identify_tools(desk, read_photo)
        + search_tools(cards, embed)
        + repair_tools(jobs, desk)
        + media_tools(desk, jobs, read_photo)
        + inventory_tools(inventory, desk)
        + close_tools(jobs, cards, inventory, desk, embed)
        + quote_tools(quotes, bot, desk),
        before_tool_callback=gate_guard(jobs.load),
    )
