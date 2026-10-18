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
from models.tools import AlreadyParked, ParkedPlan, ProposedStep, StartRepairIn, StepTranslations
from tools import repair, translate_steps
from tools.gates import open_gate

Ask = Callable[[str, type[StepTranslations]], Awaitable[StepTranslations]]
logger = logging.getLogger(__name__)


def repair_tools(jobs: JobStore, desk: MediaDesk, ask: Ask = ask_json) -> list[FunctionTool]:
    desk.load_job = lambda: jobs.load(desk.job_id)

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
        tool_context: ToolContext,
        card_ids: list[str] | None = None,
        steps: list[ProposedStep] | None = None,
        manual_request_id: str | None = None,
    ) -> dict:
        """Starts guiding a repair. Pass the IDs of the fault cards you are using, or, to guide the printed steps of
        his manual page, the `manual_request_id` its photo's result gave you. Only when no card or manual
        matched, pass your proposed steps instead, each with `instruction` in the reply language and
        `summary_en`, one line of English. Returns the number of steps and their sources, not their text: get
        each step from next_step. STOP_REFER means a step is not allowed: tell him a certified technician is
        needed and offer help with the other checks."""
        inp = StartRepairIn(card_ids=card_ids or [], steps=steps or [], manual_request_id=manual_request_id)
        page = desk.pages.get(manual_request_id) if manual_request_id else None
        if manual_request_id and not (page and page.steps):
            return {"status": "NO_PAGE", "message": "No checked manual page with printed steps has that ID."}
        cards = jobs.fault_cards(inp.card_ids)
        state = tool_context.state
        out = jobs.update(state["job_id"], lambda job: repair.start_repair(inp, job, cards, page))
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
        after this returns it, and say it from `instruction_en` when present, in the reply language.
        SAFETY_GATE means his phone already asks for the photo in `required_evidence`: tell
        him what to do and what to photograph. Only that photo opens the gate, saying it is done does not; you get a
        note when it passes. DONE means every step was given."""
        return jobs.update(tool_context.state["job_id"], repair.next_step).model_dump(mode="json")

    def park_repair(tool_context: ToolContext, issue: str) -> dict:
        """He wants to deal with a side issue now ("abhi"): keeps the repair at the step he is on. Then start_repair
        for the side issue as for any repair, and resume_repair when it is done. `issue` in a few words.
        ALREADY_PARKED: one side issue is open already; tell him you noted this one and will come back to it.
        NOTHING_TO_PARK: no step was given yet, so just deal with it."""
        state = tool_context.state
        if state.get("parked"):
            state["side_issues"] = [*(state.get("side_issues") or []), issue]
            return AlreadyParked(noted=issue).model_dump(mode="json")
        out, plan = repair.park(jobs.load(state["job_id"]), issue)
        if plan is not None:
            state["parked"] = plan.model_dump(mode="json")
        return out.model_dump(mode="json")

    def resume_repair(tool_context: ToolContext) -> dict:
        """Back to the repair he was on: after he chose "baad mein" (later) for a side issue, or when the side issue
        is done. Gives the step he was on again, on his screen, through its safety gates; say it as you would a
        next_step result. SAFETY_GATE: his phone asks for that photo first."""
        state = tool_context.state
        parked = ParkedPlan.model_validate(state["parked"]) if state.get("parked") else None
        out = jobs.update(state["job_id"], lambda job: repair.resume(job, parked))
        state["parked"] = None
        return out.model_dump(mode="json")

    tools = [FunctionTool(start_repair), FunctionTool(next_step), FunctionTool(park_repair), FunctionTool(resume_repair)]
    for tool in tools:
        tool.behavior = types.Behavior.BLOCKING
    return tools
