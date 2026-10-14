"""before_tool_callback: the second gate check (docs/SAFETY.md, enforcement 2). Human-owned.

It refuses next_step and close_job while the job's next step needs a gate that has not passed. It loads the job
itself, repeats the tool's check on purpose, and reads gate state only through the pure gate logic in
tools/gates.py, never through the tool's code."""

from collections.abc import Callable
from typing import Any

from google.adk.tools import BaseTool, ToolContext

from models.repair import RepairJob
from models.tools import SafetyGateOut
from tools.gates import EVIDENCE, open_gate

GUARDED_TOOLS = {"next_step", "close_job"}


def gate_guard(load_job: Callable[[str], RepairJob]):
    """Builds the callback around the job loader (Firestore in the app, a fake in tests)."""

    def block_open_gates(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any] | None:
        """None lets the call run; a returned dict replaces the tool's result and the tool is not called."""
        if tool.name not in GUARDED_TOOLS:
            return None
        gate = open_gate(load_job(tool_context.state["job_id"]))
        if gate is None:
            return None
        return SafetyGateOut(gate_id=gate, required_evidence=EVIDENCE[gate]).model_dump()

    return block_open_gates
