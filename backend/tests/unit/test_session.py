"""Signed demo session tokens (rest.md: a signed, 24 h demo token): the worker id comes back only from an untampered,
unexpired token signed with SESSION_SECRET."""

from datetime import UTC, datetime, timedelta

from app.session import TOKEN_TTL, issue, verify

NOW = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)


def test_a_fresh_token_names_its_worker():
    assert verify(issue("w_hi_demo", NOW), NOW) == "w_hi_demo"


def test_a_token_expires_after_24_hours():
    token = issue("w_hi_demo", NOW)
    assert verify(token, NOW + TOKEN_TTL - timedelta(seconds=1)) == "w_hi_demo"
    assert verify(token, NOW + TOKEN_TTL) is None


def test_a_tampered_token_is_refused():
    payload, sig = issue("w_hi_demo", NOW).split(".")
    other_payload, _ = issue("w_te_demo", NOW).split(".")
    assert verify(f"{other_payload}.{sig}", NOW) is None
    assert verify(f"{payload}.{sig[:-2]}AA", NOW) is None


def test_a_token_signed_with_another_secret_is_refused(monkeypatch):
    token = issue("w_hi_demo", NOW)
    monkeypatch.setenv("SESSION_SECRET", "another-secret")
    assert verify(token, NOW) is None


def test_garbage_is_refused():
    for token in ("", "demo", "t", "a.b.c", "%%%.%%%"):
        assert verify(token, NOW) is None


def test_two_visitors_on_the_same_demo_worker_in_the_same_second_get_different_tokens():
    assert issue("w_hi_demo", NOW) != issue("w_hi_demo", NOW)
