"""Inventory rules (BUILD-GUIDE T18): part lookup, all-or-nothing deltas that never go below zero or invent a part,
the low flag, and the voice delta normalisation at the tool boundary (rest.md)."""

import math
from datetime import UTC, datetime

import pytest

from models.inventory import InventoryDelta
from tests.unit.fake_inventory import item, stock
from tools.inventory import StockError, apply_deltas, find, is_low, voice_delta

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def delta(part, d):
    return InventoryDelta(part=part, delta=d)


@pytest.mark.parametrize(
    ("said", "pid"),
    [
        ("Capacitor 2.5uF", "part_cap25"),
        ("capacitor 2.5 mfd", "part_cap25"),
        ("CAPACITOR 2.5 µF", "part_cap25"),
        ("fan capacitor", "part_cap25"),
        ("capacitor", "part_cap25"),
        ("outdoor board", "part_pcb"),
        ("PCB", "part_pcb"),
        ("tape", "part_tape"),
    ],
)
def test_a_part_is_found_by_name_alias_or_category(said, pid):
    assert [i.id for i in find(stock(), said)] == [pid]


def test_an_unknown_part_is_not_found():
    assert find(stock(), "compressor") == []


def test_an_unclear_part_returns_every_match():
    items = [*stock(), item("part_cap35", "Capacitor 35uF", 2, 1, "capacitor")]
    assert {i.id for i in find(items, "capacitor")} == {"part_cap25", "part_cap35"}


def test_do_capacitor_use_kiye_takes_two_off():
    (changed,) = apply_deltas(stock(), [delta("capacitor", -2)], "voice", NOW)
    assert (changed.id, changed.qty, changed.source, changed.updated_at) == ("part_cap25", 3, "voice", NOW)


def test_deltas_for_the_same_part_add_up():
    (changed,) = apply_deltas(stock(), [delta("capacitor", -2), delta("fan capacitor", 1)], "voice", NOW)
    assert changed.qty == 4


def test_an_unknown_part_is_an_error_not_a_new_part():
    with pytest.raises(StockError) as err:
        apply_deltas(stock(), [delta("capacitor", -1), delta("compressor", 1)], "voice", NOW)
    assert (err.value.reason, err.value.part) == ("unknown_part", "compressor")


def test_an_unclear_part_is_an_error():
    items = [*stock(), item("part_cap35", "Capacitor 35uF", 2, 1, "capacitor")]
    with pytest.raises(StockError) as err:
        apply_deltas(items, [delta("capacitor", -1)], "voice", NOW)
    assert err.value.reason == "ambiguous_part"


def test_stock_never_goes_below_zero():
    with pytest.raises(StockError) as err:
        apply_deltas(stock(), [delta("outdoor pcb", -1)], "voice", NOW)
    assert err.value.reason == "below_zero"


def test_low_at_the_threshold():
    assert is_low(item("part_x", "X", 2, 2))
    assert not is_low(item("part_x", "X", 3, 2))


@pytest.mark.parametrize(("said", "value"), [(-2, -2), (-2.0, -2), (3.0, 3)])
def test_voice_deltas_take_whole_numbers(said, value):
    assert voice_delta(said) == value


@pytest.mark.parametrize("said", [0, 0.0, 1.5, True, "2", math.nan, math.inf])
def test_voice_deltas_reject_anything_else(said):
    with pytest.raises(ValueError):
        voice_delta(said)


def test_a_word_inside_another_parts_name_does_not_match_it():
    items = [*stock(), item("part_cap35", "Capacitor 35+5uF", 2, 1, "capacitor", ["compressor capacitor"])]
    assert find(items, "compressor") == []
    with pytest.raises(StockError) as err:
        apply_deltas(items, [delta("compressor", 1)], "manual", NOW)
    assert err.value.reason == "unknown_part"
