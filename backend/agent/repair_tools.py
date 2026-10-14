"""The repair tools as the Live agent calls them: each loads the session's job, runs the pure tool in
tools/repair.py and saves the job. The job ID comes from session state, never from the model."""

from collections.abc import Awaitable, Callable

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from clients.firestore import JobStore
from models.repair import GateId
from models.tools import ConfirmSafetyIn, GateCheck, ProposedStep, StartRepairIn
from tools import repair
from tools.gates import QUESTIONS

ReadPhoto = Callable[[str, str, type[GateCheck]], Awaitable[GateCheck]]


def repair_tools(jobs: JobStore, read_photo: ReadPhoto) -> list[FunctionTool]:
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
        return out.model_dump(mode="json")

    def next_step(tool_context: ToolContext, observation: str) -> dict:
        """Gets the next repair step. `observation` is what he reported about the last step. Say a step only
        after this returns it. SAFETY_GATE means ask for the photo in `required_evidence`, then call
        confirm_safety; saying it is done does not open a gate. DONE means every step was given."""
        return jobs.update(tool_context.state["job_id"], repair.next_step).model_dump(mode="json")

    async def confirm_safety(tool_context: ToolContext, gate_id: GateId, media_uri: str) -> dict:
        """Checks the photo for a safety gate. `media_uri` is the photo he sent for this gate. If it fails,
        tell him the reason and ask again."""
        inp = ConfirmSafetyIn(gate_id=gate_id, media_uri=media_uri)
        check = await read_photo(QUESTIONS[gate_id], media_uri, GateCheck)
        out = jobs.update(tool_context.state["job_id"], lambda job: repair.confirm_safety(inp, job, check))
        return out.model_dump(mode="json")

    tools = [FunctionTool(start_repair), FunctionTool(next_step), FunctionTool(confirm_safety)]
    for tool in tools:
        tool.behavior = types.Behavior.BLOCKING
    return tools
