"""The Places API (New) text-search client against a fake transport: the request it makes, the places it returns,
and a failed call that never carries the API key in its error."""

import json

import httpx
import pytest

from clients.places import PlacesClient
from models.places import Place
from models.worker import Geo

KEY = "fake-places-key"


def places_with(handler) -> tuple[PlacesClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return PlacesClient(KEY, httpx.AsyncClient(transport=httpx.MockTransport(record))), seen


async def test_search_near_a_point_asks_for_only_the_fields_it_reads():
    places, seen = places_with(
        lambda r: httpx.Response(
            200,
            json={
                "places": [
                    {
                        "id": "p_1",
                        "displayName": {"text": "Shop One", "languageCode": "en"},
                        "formattedAddress": "Sector 18, Noida",
                        "location": {"latitude": 28.57, "longitude": 77.32},
                    }
                ]
            },
        )
    )
    found = await places.search("outdoor PCB spare parts shop", Geo(lat=28.5706, lng=77.3272))
    assert found == [Place(id="p_1", name="Shop One", address="Sector 18, Noida", geo=Geo(lat=28.57, lng=77.32))]
    (request,) = seen
    assert str(request.url) == "https://places.googleapis.com/v1/places:searchText"
    assert request.headers["X-Goog-Api-Key"] == KEY
    assert request.headers["X-Goog-FieldMask"] == (
        "places.id,places.displayName,places.formattedAddress,places.location"
    )
    assert json.loads(request.content) == {
        "textQuery": "outdoor PCB spare parts shop",
        "locationBias": {"circle": {"center": {"latitude": 28.5706, "longitude": 77.3272}, "radius": 5000.0}},
        "pageSize": 5,
        "regionCode": "IN",
    }


async def test_search_without_a_point_has_no_location_bias():
    places, seen = places_with(lambda r: httpx.Response(200, json={}))
    assert await places.search("PCB spare parts shop 201301", None) == []
    assert "locationBias" not in json.loads(seen[0].content)


async def test_a_failed_call_does_not_carry_the_key():
    places, _ = places_with(lambda r: httpx.Response(403, json={"error": {"message": f"bad key {KEY}"}}))
    with pytest.raises(RuntimeError) as err:
        await places.search("PCB", None)
    assert "403" in str(err.value)
    assert KEY not in str(err.value)
