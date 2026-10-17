"""save_profile_fields rules (BUILD-GUIDE T21, G1): each answer is checked and saved on its own, trades are 1 to 3
listed values and more than 3 asks for his top 3, the pincode is 6 digits, brands get one spelling, and onboarding is
done only with his trades saved."""

from datetime import UTC, datetime

import pytest

from models.worker import SaveProfileIn, Worker
from tests.unit.fake_inventory import stock
from tools.profile import fresh_worker, save_profile

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def new() -> Worker:
    return fresh_worker("w_onb_test", "te", NOW)


def save(worker=None, items=(), **answers):
    return save_profile(SaveProfileIn(**answers), worker or new(), list(items), NOW)


def test_a_fresh_worker_has_an_empty_profile_and_is_not_onboarded():
    worker = new()
    assert (worker.trades, worker.brands, worker.pincode, worker.onboarding_done, worker.demo) == ([], [], None, False, True)
    assert worker.lang == "te"


def test_an_onboarded_worker_needs_at_least_one_trade():
    with pytest.raises(ValueError, match="trade"):
        Worker.model_validate(new().model_dump() | {"onboarding_done": True})
    assert len(Worker.model_validate(new().model_dump() | {"trades": ["ac"] * 1}).trades) == 1


def test_three_trades_are_saved():
    change = save(trades=["ac", "fridge", "washing_machine"])
    assert change.out.status == "SAVED"
    assert change.worker.trades == ["ac", "fridge", "washing_machine"]
    assert change.shown == {"trades": ["ac", "fridge", "washing_machine"]}


def test_four_trades_are_not_saved_and_ask_for_his_top_three():
    change = save(trades=["ac", "fridge", "washing_machine", "geyser"])
    assert change.out.status == "ASK_AGAIN"
    assert [(p.field, p.reason) for p in change.out.problems] == [("trades", "pick_top_3")]
    assert change.worker.trades == [] and change.shown == {}


def test_an_unknown_trade_is_not_saved():
    change = save(trades=["ac", "mixer_grinder"])
    assert [(p.field, p.reason) for p in change.out.problems] == [("trades", "unknown_trade")]
    assert change.worker.trades == []


def test_a_repeated_trade_is_not_saved():
    change = save(trades=["ac", "ac"])
    assert [(p.field, p.reason) for p in change.out.problems] == [("trades", "duplicate_trade")]
    assert change.worker.trades == []


@pytest.mark.parametrize(("said", "saved"), [("201301", "201301"), ("201 301", "201301"), ("2013O1", None),
                                             ("20130", None), ("012345", None)])
def test_the_pincode_is_six_digits(said, saved):
    change = save(pincode=said)
    assert change.worker.pincode == saved
    assert (change.out.status == "SAVED") == (saved is not None)


@pytest.mark.parametrize(("years", "ok"), [(0, True), (8, True), (60, True), (61, False), (-1, False)])
def test_experience_is_a_plausible_number_of_years(years, ok):
    assert (save(experience_yrs=years).worker.experience_yrs == years) == ok


def test_brands_get_one_spelling_and_a_close_mishearing_is_corrected():
    change = save(brands=["voltaas", "lg", "DAIKIN", "Sansui"])
    assert change.worker.brands == ["Voltas", "LG", "Daikin", "Sansui"]


def test_one_bad_answer_does_not_stop_the_good_ones():
    change = save(trades=["ac"], pincode="12")
    assert change.worker.trades == ["ac"] and change.worker.pincode is None
    assert [p.field for p in change.out.problems] == ["pincode"]


def test_stock_with_a_count_is_added_and_a_part_he_does_not_keep_only_shown():
    change = save(stock=[{"part": "capacitor", "qty": 4}, {"part": "PCB", "qty": 0}, {"part": "relay"}])
    assert [(i.name, i.qty, i.source) for i in change.new_parts] == [("capacitor", 4, "voice")]
    assert change.shown["stock"] == [{"part": "capacitor", "qty": 4}, {"part": "PCB", "qty": 0},
                                     {"part": "relay", "qty": None}]


def test_stock_he_already_has_gets_his_count_instead_of_a_second_part():
    change = save(items=stock(), stock=[{"part": "fan capacitor", "qty": 7}])
    assert [(i.id, i.qty) for i in change.new_parts] == [("part_cap25", 7)]


def test_the_shop_is_kept_for_saving_as_a_vendor():
    change = save(shop="  Sharma Electricals ")
    assert change.shop == "Sharma Electricals" and change.shown == {"shop": "Sharma Electricals"}


def test_done_marks_onboarding_only_once_his_trades_are_saved():
    assert save(done=True).out.problems[0].reason == "missing"
    finished = save(worker=save(trades=["ac"]).worker, done=True)
    assert finished.worker.onboarding_done and finished.out.onboarding_done


# The conditional trades rule (firestore.md, approved Oct 17): 0 to 3 while onboarding, 1 to 3 once onboarded, never
# more than 3 and never repeated, in either state.


@pytest.mark.parametrize("onboarded", [False, True])
@pytest.mark.parametrize("trades", [["ac", "fridge", "geyser", "led_tv"], ["ac", "ac"], ["mixer"]])
def test_too_many_repeated_or_unknown_trades_are_invalid_whether_or_not_onboarded(onboarded, trades):
    with pytest.raises(ValueError):
        Worker.model_validate(new().model_dump() | {"trades": trades, "onboarding_done": onboarded})


def test_an_onboarding_worker_may_have_no_trades_yet():
    assert Worker.model_validate(new().model_dump() | {"trades": []}).trades == []
