"""The one Ustaad agent (SPEC §6). Tools are added by their own tasks."""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.models import Gemini

from agent.callbacks import gate_guard
from agent.repair_tools import repair_tools
from clients.firestore import JobStore
from clients.gemini import read_photo

INSTRUCTION = (Path(__file__).parent / "instruction.md").read_text(encoding="utf-8")


def build_ustaad(model: str, location: str, jobs: JobStore) -> Agent:
    # The Live model is served from a different region than the rest of the app (DECISIONS, Oct 13).
    return Agent(
        name="ustaad",
        model=Gemini(model=model, client_kwargs={"location": location}),
        instruction=INSTRUCTION,
        tools=repair_tools(jobs, read_photo),
        before_tool_callback=gate_guard(jobs.load),
    )
