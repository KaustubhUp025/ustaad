"""save_profile_fields as the Live agent calls it during the onboarding interview (BUILD-GUIDE T21, G1): the worker
comes from session state, the rules are tools/profile.py, and each saved answer goes to the phone's profile card as a
`profile_update` frame."""

from datetime import UTC, datetime

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from pydantic import ValidationError

from agent.media_tools import MediaDesk
from clients.firestore import InventoryStore, WorkerStore
from models.worker import ProfileProblem, SaveProfileIn, SaveProfileOut
from models.ws import ProfileUpdate
from tools.profile import ProfileChange, save_profile


def profile_tools(workers: WorkerStore, inventory: InventoryStore, desk: MediaDesk) -> list[FunctionTool]:
    async def save_profile_fields(
        tool_context: ToolContext,
        trades: list[str] | None = None,
        brands: list[str] | None = None,
        pincode: str | None = None,
        experience_yrs: int | None = None,
        stock: list[dict] | None = None,
        shop: str | None = None,
        done: bool = False,
    ) -> dict:
        """Saves his onboarding answers as he gives them; pass only the fields he just answered. `trades`: 1 to 3 of
        ac, fridge, washing_machine, led_tv, microwave, geyser, fan_cooler, other. `pincode`: the 6 digits.
        `stock`: [{"part": "capacitor", "qty": 4}], qty 0 for a part he doesn't keep, no qty if he gave no count.
        `shop`: the parts shop he buys from. `done`: true with the last answer. ASK_AGAIN lists what was not saved:
        pick_top_3 means ask him for his top 3 appliances; otherwise ask that question again."""
        try:
            inp = SaveProfileIn(
                trades=trades, brands=brands, pincode=pincode, experience_yrs=experience_yrs, stock=stock, shop=shop,
                done=done,
            )
        except ValidationError as err:
            problems = [ProfileProblem(field=str(e["loc"][0]), reason="not_plausible") for e in err.errors()]
            return SaveProfileOut(status="ASK_AGAIN", problems=problems, onboarding_done=False).model_dump()
        worker_id = tool_context.state["worker_id"]
        now = datetime.now(UTC)

        def change(worker) -> tuple[ProfileChange, object]:
            result = save_profile(inp, worker, inventory.items(worker_id), now)
            return result, result.worker

        result = workers.update(worker_id, change)
        if result.new_parts:
            inventory.update(worker_id, lambda _: (None, result.new_parts))
        if result.shop:
            workers.add_vendor(worker_id, result.shop)
        shown = result.shown | ({"onboarding_done": True} if inp.done and result.out.onboarding_done else {})
        if shown:
            await desk.show(ProfileUpdate(fields=shown))
        return result.out.model_dump()

    tool = FunctionTool(save_profile_fields)
    # He keeps talking while answers save; the result still reaches Ustaad, so a problem gets asked again.
    tool.behavior = types.Behavior.NON_BLOCKING
    tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return [tool]
