"""save_profile_fields as the Live agent calls it (BUILD-GUIDE T21): answers merge into his worker document, the card
gets a `profile_update` frame, counted stock becomes parts, the shop becomes a vendor, and Ustaad hears a problem."""

from types import SimpleNamespace

from google.genai import types

from agent.media_tools import MediaDesk
from agent.profile_tools import profile_tools
from models.worker import Worker
from tests.unit.fake_inventory import FakeInventoryStore
from tests.unit.test_profile import NOW
from tools.profile import fresh_worker


class FakeWorkers:
    def __init__(self, worker: Worker) -> None:
        self.worker = worker
        self.vendors: list[str] = []

    def update(self, worker_id, change):
        out, self.worker = change(self.worker)
        return out

    def add_vendor(self, worker_id, name):
        self.vendors.append(name)


class Desk(MediaDesk):
    def __init__(self) -> None:
        super().__init__("j_1", "bucket")
        self.shown = []

    async def show(self, frame) -> None:
        self.shown.append(frame)


def setup():
    workers, inventory, desk = FakeWorkers(fresh_worker("w_onb_1", "hi", NOW)), FakeInventoryStore([]), Desk()
    (tool,) = profile_tools(workers, inventory, desk)
    return workers, inventory, desk, tool, SimpleNamespace(state={"worker_id": "w_onb_1"})


def test_ustaad_keeps_talking_and_hears_the_result_when_idle():
    *_, tool, _ = setup()
    assert (tool.name, tool.behavior) == ("save_profile_fields", types.Behavior.NON_BLOCKING)
    # Not SILENT: "pick your top 3" and a bad pincode must reach him so he asks again.
    assert tool.response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE


async def test_the_g1_answers_fill_the_card_and_his_profile():
    workers, inventory, desk, tool, ctx = setup()
    answers = [
        {"trades": ["ac", "fridge"]},
        {"brands": ["Voltas", "LG", "Daikin"]},
        {"pincode": "201301"},
        {"experience_yrs": 8},
        {"stock": [{"part": "capacitor", "qty": 4}, {"part": "PCB", "qty": 0}]},
        {"shop": "Sharma Electricals", "done": True},
    ]
    for args in answers:
        out = await tool.run_async(args=args, tool_context=ctx)
        assert out["status"] == "SAVED"
    assert out["onboarding_done"] is True
    w = workers.worker
    assert (w.trades, w.brands, w.pincode, w.experience_yrs, w.onboarding_done) == (
        ["ac", "fridge"], ["Voltas", "LG", "Daikin"], "201301", 8, True)
    assert [(i.name, i.qty) for i in inventory.items("w_onb_1")] == [("capacitor", 4)]
    assert workers.vendors == ["Sharma Electricals"]
    assert [list(f.fields) for f in desk.shown] == [["trades"], ["brands"], ["pincode"], ["experience_yrs"],
                                                   ["stock"], ["shop", "onboarding_done"]]


async def test_four_appliances_change_nothing_and_tell_ustaad_to_ask_for_the_top_three():
    workers, _, desk, tool, ctx = setup()
    out = await tool.run_async(args={"trades": ["ac", "fridge", "geyser", "led_tv"]}, tool_context=ctx)
    assert out["status"] == "ASK_AGAIN" and out["problems"] == [{"field": "trades", "reason": "pick_top_3"}]
    assert workers.worker.trades == [] and desk.shown == []


async def test_a_malformed_call_is_an_answer_for_ustaad_not_a_crash():
    _, _, desk, tool, ctx = setup()
    out = await tool.run_async(args={"experience_yrs": "aath"}, tool_context=ctx)
    assert out["status"] == "ASK_AGAIN" and out["problems"] == [{"field": "experience_yrs", "reason": "not_plausible"}]
    assert desk.shown == []
