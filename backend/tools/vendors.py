"""Nearby parts shops for find_vendors (SPEC §6): the Places search text, and the shops nearest first with their
distance from the worker. Pure: the caller searches."""

from math import asin, cos, radians, sin, sqrt

from models.places import Place
from models.quotes import NearbyShop
from models.worker import Geo

EARTH_KM = 6371.0


def search_text(part: str, home: Geo | None, pincode: str | None) -> str:
    """With his location the search is biased around it; without, his pincode names the area."""
    text = f"{part} spare parts shop"
    return text if home is not None or not pincode else f"{text} near {pincode}"


def _km(a: Geo, b: Geo) -> float:
    h = sin(radians(b.lat - a.lat) / 2) ** 2 + cos(radians(a.lat)) * cos(radians(b.lat)) * sin(
        radians(b.lng - a.lng) / 2
    ) ** 2
    return 2 * EARTH_KM * asin(sqrt(h))


def nearby(places: list[Place], home: Geo | None) -> list[NearbyShop]:
    shops = [
        NearbyShop(
            name=p.name,
            address=p.address,
            distance_km=round(_km(home, p.geo), 1) if home is not None and p.geo is not None else None,
        )
        for p in places
    ]
    if home is None:
        return shops
    return sorted(shops, key=lambda s: (s.distance_km is None, s.distance_km or 0))
