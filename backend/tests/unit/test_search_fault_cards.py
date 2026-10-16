"""search_fault_cards (SPEC §6): brand-filtered vector query, exact code matches first, top 5 with a citation, and
never the step text (steps reach the model only through next_step)."""

import pytest

from models.fault_card import FaultCard
from models.tools import SearchFaultCardsIn
from tests.unit.fake_cards import FakeCardStore, embed
from tools.search_fault_cards import MAX_RESULTS, canonical_brand, search_fault_cards


def card(cid, code, symptom, brand="Voltas", appliance_type="split_ac"):
    return FaultCard(
        id=cid,
        created_at="2026-10-16T00:00:00Z",
        brand=brand,
        error_code=code,
        symptom=symptom,
        **({"appliance_type": appliance_type} if appliance_type else {}),
        fix_steps=["Test step text that must not leak"],
        hazard="HV",
        source={"type": "whatsapp_voice", "author": "Samyak", "date": "2026-10-16", "audio_uri": "gs://b/a.flac",
                "message_ids": ["m2"]},
        confidence=0.9,
    )


def seeded() -> FakeCardStore:
    store = FakeCardStore()
    cards = [
        card("fc_e6", "E6", "outdoor unit not running"),
        card("fc_drip", "", "water dripping from indoor unit"),
        card("fc_remote", "", "remote not working"),
        card("fc_e1", "E1", "room sensor test symptom"),
        card("fc_e6_daikin", "E6", "outdoor unit not running", brand="Daikin"),
        card("fc_lg_ch05", "CH05", "indoor display shows code", brand="LG"),
        card("fc_lg_tv", "", "no picture on screen", brand="LG", appliance_type="led_tv"),
        card("fc_lg_untyped", "", "no picture on screen display", brand="LG", appliance_type=None),
        *[card(f"fc_x{i}", f"X{i}", f"outdoor unit test symptom {i}") for i in range(6)],
    ]
    for c in cards:
        store.save(c, embed([f"{c.brand} {c.error_code} {c.symptom}"], "RETRIEVAL_DOCUMENT")[0])
    return store


def test_voltas_e6_returns_the_e6_card_first_with_its_citation():
    out = search_fault_cards(SearchFaultCardsIn(brand="Voltas", error_code="E6"), embed, seeded().nearest)
    top = out.cards[0]
    assert top.card_id == "fc_e6"
    assert top.citation.model_dump() == {"author": "Samyak", "date": "2026-10-16", "audio_uri": "gs://b/a.flac"}


def test_a_code_match_ranks_above_a_closer_symptom_match():
    inp = SearchFaultCardsIn(brand="Voltas", error_code="e6 ", symptom="water dripping from indoor unit")
    assert search_fault_cards(inp, embed, seeded().nearest).cards[0].card_id == "fc_e6"


def test_without_a_code_the_symptom_ranks():
    inp = SearchFaultCardsIn(brand="Voltas", symptom="water dripping from indoor unit")
    assert search_fault_cards(inp, embed, seeded().nearest).cards[0].card_id == "fc_drip"


def test_only_the_asked_brand_is_queried_and_at_most_five_return():
    store = seeded()
    out = search_fault_cards(SearchFaultCardsIn(brand="Voltas", symptom="outdoor unit"), embed, store.nearest)
    assert len(out.cards) == MAX_RESULTS
    assert {c.brand for c in out.cards} == {"Voltas"}
    assert store.queries[0][0] == "Voltas"


def test_the_result_never_carries_step_text():
    out = search_fault_cards(SearchFaultCardsIn(brand="Voltas", error_code="E6"), embed, seeded().nearest)
    assert "must not leak" not in out.model_dump_json()
    assert out.cards[0].steps == 1


def test_no_cards_for_the_brand_gives_an_empty_list():
    assert search_fault_cards(SearchFaultCardsIn(brand="Onida"), embed, seeded().nearest).cards == []


@pytest.mark.parametrize(
    ("given", "stored"),
    [("VOLTAS", "Voltas"), (" voltas ", "Voltas"), ("lg", "LG"), ("blue  star", "Blue Star"), ("IFB", "IFB")],
)
def test_brands_are_compared_in_one_spelling(given, stored):
    assert canonical_brand(given) == stored


def test_the_brand_search_ignores_case():
    out = search_fault_cards(SearchFaultCardsIn(brand="VOLTAS", error_code="E6"), embed, seeded().nearest)
    assert out.cards[0].card_id == "fc_e6"


def test_an_lg_tv_query_never_returns_ac_or_untyped_cards():
    inp = SearchFaultCardsIn(brand="LG", appliance_type="led_tv", symptom="no picture on screen")
    assert [c.card_id for c in search_fault_cards(inp, embed, seeded().nearest).cards] == ["fc_lg_tv"]


def test_an_unrelated_symptom_returns_nothing():
    inp = SearchFaultCardsIn(brand="Voltas", symptom="burning smell from fan blade")
    assert search_fault_cards(inp, embed, seeded().nearest).cards == []


def test_an_exact_code_match_is_returned_even_below_the_floor():
    inp = SearchFaultCardsIn(brand="Voltas", error_code="E1", symptom="burning smell from fan blade")
    assert [c.card_id for c in search_fault_cards(inp, embed, seeded().nearest).cards] == ["fc_e1"]
