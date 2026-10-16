"""check_inventory / update_inventory as the Live agent calls them (SPEC §6, BUILD-GUIDE T18): the worker comes from
session state, every part touched is shown to the phone as a `stock` frame, and a bad call changes nothing."""

from types import SimpleNamespace

from google.genai import types

from agent.inventory_tools import inventory_tools
from agent.media_tools import MediaDesk
from tests.unit.fake_inventory import FakeInventoryStore, stock


class Desk(MediaDesk):
    def __init__(self) -> None:
        super().__init__("j_1", "bucket")
        self.shown = []

    async def show(self, frame) -> None:
        self.shown.append(frame)


def setup():
    store, desk = FakeInventoryStore(stock()), Desk()
    check, update = inventory_tools(store, desk)
    return store, desk, check, update, SimpleNamespace(state={"worker_id": "w_hi_demo"})


def test_check_is_blocking_and_update_is_silent():
    _, _, check, update, _ = setup()
    assert (check.name, check.behavior) == ("check_inventory", types.Behavior.BLOCKING)
    assert (update.name, update.behavior) == ("update_inventory", types.Behavior.NON_BLOCKING)
    assert update.response_scheduling == types.FunctionResponseScheduling.SILENT


async def test_pcb_nahi_hai_shows_zero_stock():
    _, desk, check, _, ctx = setup()
    out = await check.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out == {"items": [{"part": "Outdoor PCB", "qty": 0, "min_qty": 1, "low": True}]}
    (frame,) = desk.shown
    assert (frame.type, frame.part, frame.qty, frame.low) == ("stock", "Outdoor PCB", 0, True)


async def test_a_part_not_in_stock_returns_nothing():
    _, desk, check, _, ctx = setup()
    assert await check.run_async(args={"part": "compressor"}, tool_context=ctx) == {"items": []}
    assert desk.shown == []


async def test_do_capacitor_use_kiye_takes_two_off_and_shows_it():
    store, desk, _, update, ctx = setup()
    out = await update.run_async(args={"deltas": [{"part": "capacitor", "delta": -2.0}]}, tool_context=ctx)
    assert out == {
        "status": "UPDATED",
        "items": [{"part": "Capacitor 2.5uF", "qty": 3, "min_qty": 2, "low": False}],
    }
    assert store.by_worker["w_hi_demo"]["part_cap25"].qty == 3
    assert store.by_worker["w_hi_demo"]["part_cap25"].source == "voice"
    assert [(f.part, f.qty) for f in desk.shown] == [("Capacitor 2.5uF", 3)]


async def test_an_unknown_part_changes_nothing():
    store, desk, _, update, ctx = setup()
    deltas = [{"part": "capacitor", "delta": -1}, {"part": "compressor", "delta": -1}]
    out = await update.run_async(args={"deltas": deltas}, tool_context=ctx)
    assert out == {"status": "NOT_UPDATED", "reason": "unknown_part", "part": "compressor"}
    assert store.by_worker["w_hi_demo"]["part_cap25"].qty == 5
    assert desk.shown == []


async def test_a_fractional_delta_changes_nothing():
    store, _, _, update, ctx = setup()
    out = await update.run_async(args={"deltas": [{"part": "capacitor", "delta": 1.5}]}, tool_context=ctx)
    assert out == {"status": "NOT_UPDATED", "reason": "bad_delta", "part": "capacitor"}
    assert store.by_worker["w_hi_demo"]["part_cap25"].qty == 5
