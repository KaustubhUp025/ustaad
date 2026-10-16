"""Admission for /ws/live (SPEC §5): new connections per IP per minute, and open Live sessions per instance."""

from app.admission import LIVE_SESSIONS, RATE_PER_MIN, Admission


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_an_ip_gets_its_rate_per_minute_then_waits():
    clock = Clock()
    admission = Admission(clock)
    assert all(admission.allow("1.2.3.4") for _ in range(RATE_PER_MIN))
    assert not admission.allow("1.2.3.4")
    clock.now = 60.1
    assert admission.allow("1.2.3.4")


def test_each_ip_has_its_own_count():
    admission = Admission(Clock())
    for _ in range(RATE_PER_MIN):
        admission.allow("1.2.3.4")
    assert admission.allow("5.6.7.8")


def test_live_sessions_are_capped_and_a_closed_one_frees_its_slot():
    admission = Admission(Clock())
    assert all(admission.acquire() for _ in range(LIVE_SESSIONS))
    assert not admission.acquire()
    admission.release()
    assert admission.open_sessions == LIVE_SESSIONS - 1
    assert admission.acquire()
