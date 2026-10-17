"""The repair tools as the Live agent calls them: each loads the session's job, runs the pure tool in
tools/repair.py and saves the job. The job ID comes from session state, never from the model. A gate photo is
judged on its own server-issued request (agent/media_tools.py), so there is no tool that takes a photo URI."""

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from agent.media_tools import MediaDesk
from clients.firestore import JobStore
from models.tools import ProposedStep, StartRepairIn
from tools import repair
from tools.gates import open_gate


def repair_tools(jobs: JobStore, desk: MediaDesk) -> list[FunctionTool]:
    def start_repair(
        tool_context: ToolContext, card_ids: list[str] | None = None, steps: list[ProposedStep] | None = None
    ) -> dict:
        """Starts guiding a repair. Pass the IDs of the fault cards you are using. Only when no card or manual
        matched, pass your proposed steps instead, each with `instruction` in the worker's language and
        `summary_en`, one line of English. Returns the number of steps and their sources, not their text: get
        each step from next_step. STOP_REFER means a step is not allowed: tell him a certified technician is
        needed and offer help with the other checks."""
        inp = StartRepairIn(card_ids=card_ids or [], steps=steps or [])
        cards = jobs.fault_cards(inp.card_ids)
        out = jobs.update(tool_context.state["job_id"], lambda job: repair.start_repair(inp, job, cards))
        # Ustaad often says the first step without calling next_step (phone test, Oct 17), so a gate before it is
        # shown now, by the server, not left to him.
        gate = out.status == "STARTED" and open_gate(jobs.load(tool_context.state["job_id"]))
        if gate:
            desk.spawn(desk.show_gate(gate))
        return out.model_dump(mode="json")

    def next_step(tool_context: ToolContext, observation: str) -> dict:
        """Gets the next repair step. `observation` is what he reported about the last step. Say a step only
        after this returns it, and say it from `instruction_en` when present, in the language he last spoke.
        SAFETY_GATE means his phone already asks for the photo in `required_evidence`: tell
        him what to do and what to photograph. Only that photo opens the gate, saying it is done does not; you get a
        note when it passes. DONE means every step was given."""
        return jobs.update(tool_context.state["job_id"], repair.next_step).model_dump(mode="json")

    tools = [FunctionTool(start_repair), FunctionTool(next_step)]
    for tool in tools:
        tool.behavior = types.Behavior.BLOCKING
    return tools
