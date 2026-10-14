"""The one Ustaad agent (SPEC §6). Tools are added by their own tasks."""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.models import Gemini

INSTRUCTION = (Path(__file__).parent / "instruction.md").read_text(encoding="utf-8")


def build_ustaad(model: str, location: str) -> Agent:
    # The Live model is served from a different region than the rest of the app (DECISIONS, Oct 13).
    return Agent(
        name="ustaad",
        model=Gemini(model=model, client_kwargs={"location": location}),
        instruction=INSTRUCTION,
    )
