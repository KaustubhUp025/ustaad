"""Test inventory (names only, no repair guidance) and an in-memory store with InventoryStore's interface."""

from collections.abc import Callable

from models.inventory import InventoryItem


def item(pid, name, qty, min_qty=1, category=None, aliases=()):
    return InventoryItem(
        id=pid,
        name=name,
        category=category,
        aliases=list(aliases),
        qty=qty,
        min_qty=min_qty,
        unit_cost_inr=None,
        source="manual",
        updated_at="2026-10-16T00:00:00Z",
    )


def stock() -> list[InventoryItem]:
    return [
        item("part_cap25", "Capacitor 2.5uF", 5, 2, "capacitor", ["fan capacitor"]),
        item("part_pcb", "Outdoor PCB", 0, 1, "pcb", ["outdoor board"]),
        item("part_tape", "Insulation tape", 10, 3),
    ]


class FakeInventoryStore:
    def __init__(self, items: list[InventoryItem]) -> None:
        self.by_worker = {"w_hi_demo": {i.id: i for i in items}}

    def items(self, worker_id: str) -> list[InventoryItem]:
        return list(self.by_worker.get(worker_id, {}).values())

    def update[T](
        self, worker_id: str, change: Callable[[list[InventoryItem]], tuple[T, list[InventoryItem]]]
    ) -> T:
        out, changed = change(self.items(worker_id))
        self.by_worker.setdefault(worker_id, {}).update({i.id: i for i in changed})
        return out
