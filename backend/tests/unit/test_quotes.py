"""The quote rules (SPEC §7, BUILD-GUIDE T19): one transition function, expiry computed on read, replies and
buttons applied to a quote, ranking, matching a vendor message to its quote, and approval."""

from datetime import timedelta

import pytest

from models.quotes import ParsedReply
from tests.unit.fake_quotes import NOW, VENDORS, sent_request
from tools import quotes

LEGAL = [
    ("CREATED", "sent", "SENT"),
    ("SENT", "reply", "PARSING"),
    ("SENT", "available", "SENT"),
    ("SENT", "declined", "DECLINED"),
    ("PARSING", "available", "PARSING"),
    ("PARSING", "quoted", "QUOTED"),
    ("PARSING", "unclear", "SENT"),
    ("PARSING", "declined", "DECLINED"),
    ("QUOTED", "available", "QUOTED"),
    ("QUOTED", "declined", "DECLINED"),
    ("QUOTED", "approved", "CONFIRMED"),
    ("CREATED", "expired", "EXPIRED"),
    ("SENT", "expired", "EXPIRED"),
    ("PARSING", "expired", "EXPIRED"),
]


@pytest.mark.parametrize(("state", "event", "after"), LEGAL)
def test_every_legal_transition(state, event, after):
    assert quotes.transition(state, event) == after


def test_the_legal_list_is_the_whole_table():
    assert {(s, e): a for s, e, a in LEGAL} == quotes.TRANSITIONS


@pytest.mark.parametrize(
    ("state", "event"), [("SENT", "approved"), ("CONFIRMED", "declined"), ("QUOTED", "reply")]
)
def test_an_illegal_transition_raises(state, event):
    with pytest.raises(quotes.IllegalTransition):
        quotes.transition(state, event)


def test_a_new_request_has_one_created_quote_per_vendor_and_expires_in_30_min():
    request, docs = quotes.new_request("qr_1", "j_1", "w_hi_demo", "outdoor PCB", "", 2, VENDORS, NOW)
    assert (request.status, request.qty, request.vendor_ids) == ("open", 2, ["v_a", "v_b", "v_c"])
    assert request.expires_at - request.created_at == timedelta(minutes=30)
    assert [(q.vendor_name, q.state, q.tg_chat_id, q.tg_message_id) for q in docs] == [
        ("Vendor A", "CREATED", 1001, None),
        ("Vendor B", "CREATED", 1002, None),
        ("Vendor C", "CREATED", 1003, None),
    ]
    assert len({q.id for q in docs}) == 3


def test_the_request_message_and_its_buttons():
    request, (quote, *_) = sent_request()
    assert quotes.request_text(request) == (
        "Ustaad stock request #qr_1\noutdoor PCB x 1\nPlease reply with price per piece and delivery time."
    )
    assert [(b.text, b.data) for b in quotes.buttons(quote.id)] == [
        ("Available", f"avail:{quote.id}"),
        ("Not available", f"na:{quote.id}"),
    ]


def test_specs_go_on_their_own_line():
    request, _ = quotes.new_request(
        "qr_2", "j_1", "w_hi_demo", "outdoor PCB", "Daikin FTKF50", 1, VENDORS, NOW
    )
    assert quotes.request_text(request).splitlines()[2] == "Specs: Daikin FTKF50"


def test_sent_stores_the_message_id():
    _, (quote, *_) = sent_request()
    assert (quote.state, quote.tg_message_id) == ("SENT", 500)


def test_expiry_is_computed_on_read():
    request, docs = sent_request()
    docs[0] = quotes.parsed(quotes.replied(docs[0], "250", False, NOW), reply(250), NOW)
    later = NOW + timedelta(minutes=30)
    read_request, read = quotes.on_read(request, docs, later)
    assert read_request.status == "expired"
    assert sorted(q.state for q in read) == ["EXPIRED", "EXPIRED", "QUOTED"]
    assert quotes.on_read(request, docs, later - timedelta(seconds=1))[0].status == "open"


def reply(price=None, available=None, eta=None, eta_minutes=None, confidence=0.9):
    return ParsedReply(
        price_inr=price, available=available, eta=eta, eta_minutes=eta_minutes, confidence=confidence
    )


def test_a_priced_reply_becomes_a_quote():
    _, (quote, *_) = sent_request()
    parsing = quotes.replied(quote, "250 rs piece, kal tak de dunga", False, NOW)
    assert (parsing.state, parsing.raw_text) == ("PARSING", "250 rs piece, kal tak de dunga")
    done = quotes.parsed(parsing, reply(250, True, "kal tak", 1440), NOW)
    assert (
        done.state,
        done.price_inr,
        done.available,
        done.eta,
        done.eta_minutes,
        done.parsed_confidence,
    ) == ("QUOTED", 250, True, "kal tak", 1440, 0.9)


def test_nahi_hai_declines():
    _, (quote, *_) = sent_request()
    done = quotes.parsed(quotes.replied(quote, "nahi hai", False, NOW), reply(available=False), NOW)
    assert (done.state, done.available) == ("DECLINED", False)


@pytest.mark.parametrize("parse", [reply(available=True, eta="1 ghante"), reply(250, confidence=0.3)])
def test_an_unclear_reply_waits_for_another_and_keeps_what_was_said(parse):
    _, (quote, *_) = sent_request()
    done = quotes.parsed(quotes.replied(quote, "haan", False, NOW), parse, NOW)
    assert (done.state, done.price_inr) == ("SENT", None)


def test_buttons():
    _, (quote, *_) = sent_request()
    assert (quotes.pressed(quote, "avail", NOW).available, quotes.pressed(quote, "avail", NOW).state) == (
        True,
        "SENT",
    )
    assert quotes.pressed(quote, "na", NOW).state == "DECLINED"
    with pytest.raises(quotes.IllegalTransition):
        quotes.pressed(quote, "other", NOW)


def test_ranking_available_then_price_then_eta():
    _, docs = sent_request()
    a, b, c = docs
    a = quotes.parsed(quotes.replied(a, "", False, NOW), reply(300, True, "aaj", 120), NOW)
    b = quotes.parsed(quotes.replied(b, "", False, NOW), reply(available=False), NOW)
    c = quotes.parsed(quotes.replied(c, "", True, NOW), reply(300, True, "1 ghanta", 60), NOW)
    cheap_slow = a.model_copy(update={"id": "q_cheap", "price_inr": 250, "eta_minutes": 1440})
    assert [q.id for q in quotes.rank([b, a, c, cheap_slow])] == ["q_cheap", c.id, a.id, b.id]


def test_a_reply_to_our_message_finds_its_quote_else_the_latest_open_one():
    old_request, old = sent_request("qr_old", NOW - timedelta(minutes=5))
    new_request, new = sent_request("qr_new")
    candidates = [(old_request, old[0]), (new_request, new[0])]
    assert quotes.match(candidates, reply_to=old[0].tg_message_id) == (old_request, old[0])
    assert quotes.match(candidates) == (new_request, new[0])
    answered = quotes.replied(new[0], "250", False, NOW)
    assert quotes.match([(old_request, old[0]), (new_request, answered)]) == (old_request, old[0])
    assert quotes.match(candidates, quote_id=old[0].id) == (old_request, old[0])
    assert quotes.match(candidates, quote_id="q_none") is None


def test_approve_confirms_the_quote_and_the_request():
    request, docs = sent_request()
    quote = quotes.parsed(quotes.replied(docs[0], "", False, NOW), reply(250, True, "kal tak", 1440), NOW)
    approved, confirmed = quotes.approve(request, quote, NOW)
    assert (approved.status, approved.approved_quote_id, confirmed.state) == (
        "approved",
        quote.id,
        "CONFIRMED",
    )
    assert quotes.confirm_text(approved, confirmed) == (
        "Ustaad order #qr_1 confirmed\noutdoor PCB x 1 at Rs 250 per piece\nDelivery: kal tak"
    )


def test_approve_needs_a_quote_and_an_open_request():
    request, docs = sent_request()
    with pytest.raises(quotes.IllegalTransition):
        quotes.approve(request, docs[0], NOW)
    quote = quotes.parsed(quotes.replied(docs[0], "", False, NOW), reply(250), NOW)
    with pytest.raises(quotes.RequestClosed):
        quotes.approve(request, quote, NOW + timedelta(minutes=31))
