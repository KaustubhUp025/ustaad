"""close_job as the Live agent calls it (T22, G4): closes the job through the pure tool, saves the job's card with its
embedding, takes the parts used off his stock (B's inventory rules, not a copy) and tells the phone `job_closed`."""

from datetime import UTC, datetime
from uuid import uuid4

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from agent.media_tools import MediaDesk
from clients.firestore import CardStore, InventoryStore, JobStore
from jobs.ingest.cards import card_text
from models.tools import CloseJobIn
from models.ws import JobClosed, Stock
from tools import inventory
from tools.close_job import close_job as close
from tools.close_job import stock_deltas
from tools.search_fault_cards import Embed


def close_tools(jobs: JobStore, cards: CardStore, stock: InventoryStore, desk: MediaDesk, embed: Embed) -> list[FunctionTool]:
    async def close_job(
        tool_context: ToolContext,
        symptom: str,
        outcome: str,
        fix_summary: str,
        parts_used: list[dict] | None = None,
        brand: str | None = None,
        error_code: str | None = None,
        appliance_type: str | None = None,
    ) -> dict:
        """Closes the job once he says it is fixed and has told you what caused it (`outcome`) and what fixed it
        (`fix_summary`), in his words. `parts_used`: [{"part": "capacitor", "qty": 1}]. Pass the brand, code and
        appliance type you know from the job. His stock goes down by the parts used; `stock_not_updated` says why it
        did not. ALREADY_CLOSED: the job was closed before; say so briefly."""
        inp = CloseJobIn(
            symptom=symptom,
            outcome=outcome,
            fix_summary=fix_summary,
            parts_used=parts_used or [],
            brand=brand,
            error_code=error_code,
            appliance_type=appliance_type,
        )
        now = datetime.now(UTC)
        made = {}

        def change(job):
            out, job, made["card"] = close(inp, job, f"fc_{uuid4().hex[:16]}", now)
            return out, job

        out = jobs.update(tool_context.state["job_id"], change)
        card = made["card"]
        if card is None:
            return out.model_dump(mode="json")
        cards.save(card, embed([card_text(card)], "RETRIEVAL_DOCUMENT")[0])
        result = out.model_dump(mode="json")
        deltas = stock_deltas(inp.parts_used)
        if deltas:

            def take(items):
                changed = inventory.apply_deltas(items, deltas, "voice", now)
                return changed, changed

            try:
                for item in stock.update(tool_context.state["worker_id"], take):
                    await desk.show(Stock(**inventory.stock_line(item).model_dump()))
            except inventory.StockError as err:
                result["stock_not_updated"] = err.reason
        await desk.show(JobClosed(job_id=tool_context.state["job_id"], card_id=card.id))
        return result

    tool = FunctionTool(close_job)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
