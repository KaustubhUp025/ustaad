"""close_job as the Live agent calls it (agent/close_tools.py): the card is saved, the parts come off his stock and the
phone gets `job_closed`, so the step card goes away (G4)."""

from types import SimpleNamespace

from agent.close_tools import close_tools
from agent.media_tools import MediaDesk
from models.repair import RepairJob
from models.ws import JobClosed, Stock
from tests.unit.fake_cards import FakeCardStore, embed
from tests.unit.fake_inventory import FakeInventoryStore, stock
from tests.unit.test_close_job import FIXTURE
from tests.unit.test_request_media import FakeJobs, FakeQueue, Phone

CONTEXT = SimpleNamespace(state={"job_id": "j_g4", "worker_id": "w_hi_demo"})


def setup():
    desk = MediaDesk("j_g4", "media")
    phone = Phone()
    desk.attach(phone.send, FakeQueue(), "en")
    jobs, cards, inventory = FakeJobs(RepairJob.model_validate(FIXTURE["job"])), FakeCardStore(), FakeInventoryStore(stock())
    tool = close_tools(jobs, cards, inventory, desk, embed)[0]
    return tool, jobs, cards, inventory, phone


async def test_g4_closing_saves_the_card_takes_the_part_off_stock_and_tells_the_phone():
    tool, jobs, cards, inventory, phone = setup()
    out = await tool.func(CONTEXT, **FIXTURE["close"])
    assert out["status"] == "CLOSED"
    (card, vector), = cards.cards.values()
    assert card.id == out["card_id"] and card.source.type == "job" and len(vector) == 768
    assert jobs.job.status == "closed"
    assert [(i.name, i.qty) for i in inventory.items("w_hi_demo") if i.id == "part_cap25"] == [("Capacitor 2.5uF", 4)]
    assert phone.of(Stock)[0].qty == 4
    assert phone.of(JobClosed) == [JobClosed(job_id="j_g4", card_id=out["card_id"])]


async def test_a_second_close_saves_nothing_and_changes_no_stock():
    tool, _, cards, inventory, phone = setup()
    await tool.func(CONTEXT, **FIXTURE["close"])
    out = await tool.func(CONTEXT, **FIXTURE["close"])
    assert out["status"] == "ALREADY_CLOSED"
    assert len(cards.cards) == 1 and len(phone.of(JobClosed)) == 1
    assert next(i.qty for i in inventory.items("w_hi_demo") if i.id == "part_cap25") == 4


async def test_a_part_not_in_stock_still_closes_the_job_and_says_why():
    tool, jobs, cards, _, _ = setup()
    out = await tool.func(CONTEXT, **(FIXTURE["close"] | {"parts_used": [{"part": "test unknown part", "qty": 1}]}))
    assert out["status"] == "CLOSED" and out["stock_not_updated"] == "unknown_part"
    assert jobs.job.status == "closed" and len(cards.cards) == 1
