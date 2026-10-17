"""Nearby parts shops from Places, nearest first, with their distance from the worker (SPEC §6 find_vendors)."""

from models.places import Place
from models.quotes import NearbyShop
from models.worker import Geo
from tools import vendors

HOME = Geo(lat=28.5706, lng=77.3272)


def place(pid: str, lat: float, lng: float) -> Place:
    return Place(id=pid, name=f"Shop {pid}", address=f"{pid} market", geo=Geo(lat=lat, lng=lng))


def test_nearest_first_in_km_to_one_decimal():
    far, near = place("far", 28.6706, 77.3272), place("near", 28.5806, 77.3272)
    assert vendors.nearby([far, near], HOME) == [
        NearbyShop(name="Shop near", address="near market", distance_km=1.1),
        NearbyShop(name="Shop far", address="far market", distance_km=11.1),
    ]


def test_without_his_location_the_distance_is_unknown_and_the_order_is_kept():
    a, b = place("a", 28.6, 77.3), place("b", 28.5, 77.3)
    assert [(s.name, s.distance_km) for s in vendors.nearby([a, b], None)] == [("Shop a", None), ("Shop b", None)]


def test_the_search_text_names_the_part_and_his_pincode_when_there_is_no_location():
    assert vendors.search_text("outdoor PCB", HOME, "201301") == "outdoor PCB spare parts shop"
    assert vendors.search_text("outdoor PCB", None, "201301") == "outdoor PCB spare parts shop near 201301"
