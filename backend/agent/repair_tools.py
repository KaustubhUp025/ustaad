"""The repair tools as the Live agent calls them: each loads the session's job, runs the pure tool in
tools/repair.py and saves the job. The job ID comes from session state, never from the model. A gate photo is
judged on its own server-issued request (agent/media_tools.py), so there is no tool that takes a photo URI."""

import logging
from collections.abc import Awaitable, Callable

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from agent.media_tools import MediaDesk
from clients.firestore import JobStore
from clients.gemini import ask_json
from models.tools import ProposedStep, StartRepairIn, StepTranslations
from tools import repair, translate_steps
from tools.gates import open_gate

Ask = Callable[[str, type[StepTranslations]], Awaitable[StepTranslations]]
logger = logging.getLogger(__name__)


def repair_tools(jobs: JobStore, desk: MediaDesk, ask: Ask = ask_json) -> list[FunctionTool]:
    async def translate(job_id: str, lang: str, language_name: str) -> None:
        """One Flash call for all the job's step cards, after the start: nothing waits for it, and on a failure the
        cards show the original words."""
        asked = translate_steps.sources(jobs.load(job_id))
        try:
            out = await ask(translate_steps.prompt(asked, language_name), StepTranslations)
        except Exception as exc:  # noqa: BLE001 — a failed translation only means the original words show
            # Only the class: the error text can carry the prompt, i.e. the steps.
            logger.warning("step translation failed (%s)", type(exc).__name__)
            return
        jobs.update(job_id, lambda job: (None, translate_steps.apply(job, lang, asked, out.lines)))

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
        state = tool_context.state
        out = jobs.update(state["job_id"], lambda job: repair.start_repair(inp, job, cards))
        # Ustaad often says the first step without calling next_step (phone test, Oct 17), so a gate before it is
        # shown now, by the server, not left to him.
        gate = out.status == "STARTED" and open_gate(jobs.load(state["job_id"]))
        if gate:
            desk.spawn(desk.show_gate(gate))
        if out.status == "STARTED" and state["lang"] in translate_steps.TRANSLATED_LANGS:
            desk.spawn(translate(state["job_id"], state["lang"], state["language_name"]))
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
