"""identify_appliance (SPEC §6, BUILD-GUIDE T12): the 6 golden photos against Flash's recorded answers, the type and
code normalisation, the trades -> card types mapping, and the agent tool's checks."""

from pathlib import Path
from typing import get_args

import pytest
from google.genai import types

from agent.identify_tools import identify_tools
from agent.media_tools import MediaDesk
from models.repair import TRADE_TYPES, ApplianceType, Trade
from models.tools import MIN_CONFIDENCE, NameplateRead
from tools.identify import identify, normalise_code, normalise_type

RECORDED = Path(__file__).parents[3] / "seed" / "fixtures" / "identify"

# Written from golden_photos/answers.md before the answers were recorded. model None = not checked: the Voltas
# photo is a BEE energy label, not a rating plate.
GOLDEN = {
    "display_e6": ("Voltas", None, "split_ac", "E6"),
    "nameplate_voltas": ("Voltas", None, "split_ac", None),
    "nameplate_lg": ("LG", "HS-09ISS", "split_ac", None),
    "display_washer_ie": (None, None, "washing_machine", "IE"),
    "nameplate_daikin": ("Daikin", "RXMQ5TVE6", "split_ac", None),
}


def recorded(name: str) -> NameplateRead:
    return NameplateRead.model_validate_json((RECORDED / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", GOLDEN)
def test_golden_photo(name):
    brand, model, kind, code = GOLDEN[name]
    out = identify(recorded(name))
    assert (out.brand, out.type, out.error_code) == (brand, kind, code)
    if model:
        assert out.model.replace(" ", "").upper() == model
    assert out.confidence >= MIN_CONFIDENCE


def test_golden_photo_capacitor_has_nothing_to_identify():
    out = identify(recorded("capacitor_no_label"))
    assert (out.brand, out.model, out.error_code) == (None, None, None)
    assert out.type in (None, "other")
    assert not out.readable


@pytest.mark.parametrize(
    ("said", "value"),
    [
        ("split_ac", "split_ac"),
        ("Split AC", "split_ac"),
        ("Inverter air conditioner (outdoor unit)", "split_ac"),
        ("Window AC", "window_ac"),
        ("Refrigerator", "fridge"),
        ("Front-load washing machine", "washing_machine"),
        ("LED TV", "led_tv"),
        ("Microwave oven", "microwave"),
        ("Water heater", "geyser"),
        ("Air cooler", "fan_cooler"),
        ("Ceiling fan", "fan_cooler"),
        ("Inverter battery", "other"),
        (None, None),
    ],
)
def test_type_is_normalised_to_the_appliance_type_values(said, value):
    assert normalise_type(said) == value


def test_every_appliance_type_value_normalises_to_itself():
    for value in get_args(ApplianceType):
        assert normalise_type(value) == value


@pytest.mark.parametrize(("shown", "code"), [(" e6 ", "E6"), ("E 6", "E6"), ("ch05", "CH05"), ("", None), (None, None)])
def test_the_code_is_kept_as_shown_in_capitals_without_spaces(shown, code):
    assert normalise_code(shown) == code


def test_trades_map_to_card_types():
    assert set(TRADE_TYPES) == set(get_args(Trade))
    assert TRADE_TYPES["ac"] == ["split_ac", "window_ac"]
    assert all(TRADE_TYPES[t] == [t] for t in get_args(Trade) if t != "ac")


class Desk(MediaDesk):
    def __init__(self) -> None:
        super().__init__("j_1", "bucket")
        self.shown = []

    async def show(self, frame) -> None:
        self.shown.append(frame)


def read_photo_returning(answer: NameplateRead):
    calls = []

    async def read_photo(question, uri, schema):
        calls.append(uri)
        return answer

    return read_photo, calls


def test_identify_appliance_is_blocking():
    (tool,) = identify_tools(Desk(), read_photo_returning(recorded("display_e6"))[0])
    assert (tool.name, tool.behavior) == ("identify_appliance", types.Behavior.BLOCKING)


async def test_the_tool_shows_the_identified_frame_and_returns_the_reading():
    desk = Desk()
    read_photo, calls = read_photo_returning(recorded("display_e6"))
    (tool,) = identify_tools(desk, read_photo)
    out = await tool.run_async(args={"media_uri": "gs://bucket/jobs/j_1/r_1/a.jpg"}, tool_context=None)
    assert calls == ["gs://bucket/jobs/j_1/r_1/a.jpg"]
    assert (out["brand"], out["error_code"], out["type"]) == ("Voltas", "E6", "split_ac")
    (frame,) = desk.shown
    assert (frame.type, frame.brand, frame.error_code) == ("identified", "Voltas", "E6")


@pytest.mark.parametrize("uri", ["gs://bucket/jobs/j_2/r_1/a.jpg", "gs://other/jobs/j_1/r_1/a.jpg", "https://x/a.jpg"])
async def test_a_photo_outside_this_jobs_folder_is_not_read(uri):
    desk = Desk()
    read_photo, calls = read_photo_returning(recorded("display_e6"))
    (tool,) = identify_tools(desk, read_photo)
    out = await tool.run_async(args={"media_uri": uri}, tool_context=None)
    assert calls == [] and desk.shown == []
    assert (out["brand"], out["confidence"]) == (None, 0)


async def test_a_failed_vision_call_returns_nothing_read():
    async def failing(question, uri, schema):
        raise TimeoutError

    desk = Desk()
    (tool,) = identify_tools(desk, failing)
    out = await tool.run_async(args={"media_uri": "gs://bucket/jobs/j_1/r_1/a.jpg"}, tool_context=None)
    assert (out["error_code"], out["confidence"]) == (None, 0)
    assert desk.shown == []


async def test_a_readable_nameplate_sets_the_brand_a_manual_page_is_checked_against():
    desk = Desk()
    (tool,) = identify_tools(desk, read_photo_returning(recorded("nameplate_voltas"))[0])
    await tool.func(media_uri="gs://bucket/jobs/j_1/r_1/a.jpg")
    assert desk.brand == "Voltas"
