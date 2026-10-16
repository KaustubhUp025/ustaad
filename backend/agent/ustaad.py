"""The one Ustaad agent (SPEC §6). Tools are added by their own tasks."""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.models import Gemini

from agent.callbacks import gate_guard
from agent.identify_tools import identify_tools
from agent.media_tools import MediaDesk, media_tools
from agent.repair_tools import repair_tools
from agent.search_tools import search_tools
from clients.firestore import CardStore, JobStore
from clients.gemini import embed, read_photo

INSTRUCTION = (Path(__file__).parent / "instruction.md").read_text(encoding="utf-8")


def build_ustaad(model: str, location: str, jobs: JobStore, cards: CardStore, desk: MediaDesk) -> Agent:
    # The Live model is served from a different region than the rest of the app (DECISIONS, Oct 13).
    return Agent(
        name="ustaad",
        model=Gemini(model=model, client_kwargs={"location": location}),
        instruction=INSTRUCTION,
        tools=identify_tools(desk, read_photo)
        + search_tools(cards, embed)
        + repair_tools(jobs)
        + media_tools(desk, jobs, read_photo),
        before_tool_callback=gate_guard(jobs.load),
    )
