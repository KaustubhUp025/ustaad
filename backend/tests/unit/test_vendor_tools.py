"""find_vendors as the Live agent calls it (SPEC §6): the worker comes from session state; his saved shops (the ones
request_quotes reaches) and nearby shops from Places, nearest first. A Places failure still answers with his saved
shops."""

from types import SimpleNamespace

from google.genai import types

from agent.quote_tools import vendor_tools
from models.places import Place
from models.worker import Geo
from tests.unit.fake_quotes import FakeQuoteStore

HOME = Geo(lat=28.5706, lng=77.3272)


class FakeWorkers:
    def __init__(self, geo: Geo | None = HOME) -> None:
        self.worker = SimpleNamespace(pincode="201301", geo=geo)

    def get(self, worker_id: str):
        return self.worker if worker_id == "w_hi_demo" else None


class FakePlaces:
    def __init__(self, found: list[Place] | None = None, error: Exception | None = None) -> None:
        self.found, self.error = found or [], error
        self.searches: list[tuple[str, Geo | None]] = []

    async def search(self, text: str, center: Geo | None) -> list[Place]:
        self.searches.append((text, center))
        if self.error:
            raise self.error
        return self.found


def setup(places=None, workers=None):
    places = places or FakePlaces(
        [
            Place(id="p_far", name="Far Shop", address="Sector 62", geo=Geo(lat=28.6706, lng=77.3272)),
            Place(id="p_near", name="Near Shop", address="Sector 18", geo=Geo(lat=28.5806, lng=77.3272)),
        ]
    )
    (tool,) = vendor_tools(FakeQuoteStore(), workers or FakeWorkers(), places)
    return tool, places, SimpleNamespace(state={"worker_id": "w_hi_demo", "job_id": "j_1"})


def test_find_vendors_is_blocking():
    tool, _, _ = setup()
    assert (tool.name, tool.behavior) == ("find_vendors", types.Behavior.BLOCKING)


async def test_saved_shops_and_nearby_shops_nearest_first():
    tool, places, ctx = setup()
    out = await tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out == {
        "saved": ["Vendor A", "Vendor B", "Vendor C"],
        "nearby": [
            {"name": "Near Shop", "address": "Sector 18", "distance_km": 1.1},
            {"name": "Far Shop", "address": "Sector 62", "distance_km": 11.1},
        ],
    }
    assert places.searches == [("outdoor PCB spare parts shop", HOME)]


async def test_without_his_location_the_search_names_his_pincode():
    tool, places, ctx = setup(workers=FakeWorkers(geo=None))
    await tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert places.searches == [("outdoor PCB spare parts shop near 201301", None)]


async def test_a_places_failure_still_gives_his_saved_shops(caplog):
    tool, _, ctx = setup(places=FakePlaces(error=RuntimeError("Places search failed: 403")))
    out = await tool.run_async(args={"part": "outdoor PCB"}, tool_context=ctx)
    assert out == {"saved": ["Vendor A", "Vendor B", "Vendor C"], "nearby": []}
    assert [r.getMessage() for r in caplog.records if r.name.startswith("agent")] == ["nearby shop search failed"]
