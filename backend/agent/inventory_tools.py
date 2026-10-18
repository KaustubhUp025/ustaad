"""check_inventory / update_inventory as the Live agent calls them: the worker comes from session state, never from
the model; the rules are tools/inventory.py; each part touched goes to the phone as a `stock` frame."""

from datetime import UTC, datetime

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from pydantic import ValidationError

from agent.media_tools import MediaDesk
from clients.firestore import InventoryStore
from models.inventory import InventoryDelta
from models.tools import CheckInventoryOut, InventoryNotUpdated, InventoryUpdated, StockLine
from models.ws import Stock
from tools import inventory


def inventory_tools(store: InventoryStore, desk: MediaDesk) -> list[FunctionTool]:
    async def show(lines: list[StockLine]) -> None:
        for line in lines:
            await desk.show(Stock(**line.model_dump()))

    async def check_inventory(tool_context: ToolContext, part: str) -> dict:
        """His stock of a part, by the name he uses. Check before suggesting a part. Empty `items`: he doesn't
        stock it. More than one: ask which one he means."""
        lines = [
            inventory.stock_line(i)
            for i in inventory.find(store.items(tool_context.state["worker_id"]), part)
        ]
        await show(lines)
        return CheckInventoryOut(items=lines).model_dump(mode="json")

    async def update_inventory(tool_context: ToolContext, deltas: list[dict]) -> dict:
        """Changes his stock once he says he used or bought parts, e.g. "do capacitor use kiye" ->
        [{"part": "capacitor", "delta": -2}]. Call it once per thing he says. NOT_UPDATED changes nothing: tell him
        why (part unknown or unclear, or not enough in stock). After UPDATED, confirm each changed part and its
        resulting quantity in the reply language. After NOT_UPDATED, explain its safe reason in that
        language; do not claim an update happened."""
        try:
            parsed = [InventoryDelta(part=d["part"], delta=inventory.voice_delta(d["delta"])) for d in deltas]
        except (KeyError, ValueError, ValidationError):
            part = next((str(d.get("part")) for d in deltas if isinstance(d, dict)), "")
            return InventoryNotUpdated(reason="bad_delta", part=part).model_dump(mode="json")
        now = datetime.now(UTC)

        def change(items):
            changed = inventory.apply_deltas(items, parsed, "voice", now)
            return changed, changed

        try:
            changed = store.update(tool_context.state["worker_id"], change)
        except inventory.StockError as err:
            return InventoryNotUpdated(reason=err.reason, part=err.part).model_dump(mode="json")
        lines = [inventory.stock_line(i) for i in changed]
        await show(lines)
        return InventoryUpdated(items=lines).model_dump(mode="json")

    check = FunctionTool(check_inventory)
    check.behavior = types.Behavior.BLOCKING
    update = FunctionTool(update_inventory)
    update.behavior = types.Behavior.NON_BLOCKING
    update.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return [check, update]
