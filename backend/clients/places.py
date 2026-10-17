"""Places API (New) text search over plain httpx, for nearby parts shops (SPEC §6 find_vendors). The key goes in a
header, and errors carry the status only."""

import os
from functools import cache

import httpx

from models.places import Place
from models.worker import Geo

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.id,places.displayName,places.formattedAddress,places.location"
RADIUS_M = 5000.0
RESULTS = 5


class PlacesClient:
    def __init__(self, key: str, http: httpx.AsyncClient) -> None:
        self._key = key
        self._http = http

    async def search(self, text: str, center: Geo | None) -> list[Place]:
        body: dict = {"textQuery": text, "pageSize": RESULTS, "regionCode": "IN"}
        if center is not None:
            body["locationBias"] = {
                "circle": {"center": {"latitude": center.lat, "longitude": center.lng}, "radius": RADIUS_M}
            }
        response = await self._http.post(
            URL, json=body, headers={"X-Goog-Api-Key": self._key, "X-Goog-FieldMask": FIELDS}
        )
        if response.status_code != 200:
            raise RuntimeError(f"Places search failed: {response.status_code}")
        return [
            Place(
                id=p["id"],
                name=p["displayName"]["text"],
                address=p.get("formattedAddress"),
                geo=Geo(lat=p["location"]["latitude"], lng=p["location"]["longitude"]) if "location" in p else None,
            )
            for p in response.json().get("places", [])
        ]


@cache
def places_client() -> PlacesClient:
    return PlacesClient(os.environ["PLACES_API_KEY"], httpx.AsyncClient(timeout=10))
