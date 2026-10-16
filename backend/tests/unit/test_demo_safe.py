"""Demo-safe photo checks (BUILD-GUIDE T27): a slow or failing vision call is answered from the recorded real answer
for the same question and the same image bytes; with nothing recorded the live answer is awaited."""

import asyncio
import time

import pytest

from app import demo_safe
from app.demo_safe import request_hash
from models.tools import MediaCheck

LIVE = MediaCheck(matches_expected=True, confidence=0.9, problem=None, findings=[])
RECORDED = MediaCheck(matches_expected=True, confidence=0.8, problem=None, findings=[])


class Cache:
    def __init__(self, entries=None) -> None:
        self.entries = dict(entries or {})

    def get(self, key):
        return self.entries.get(key)

    def put(self, key, response, model):
        self.entries[key] = response


def digest(uri):
    return "md5-of-" + uri.rsplit("/", 1)[-1]


def model(delay_s=0.0, fails=False):
    calls = []

    async def read_photo(question, uri, schema):
        calls.append(uri)
        await asyncio.sleep(delay_s)
        if fails:
            raise TimeoutError("Test failure")
        return LIVE

    return read_photo, calls


@pytest.fixture(autouse=True)
def short_timer(monkeypatch):
    monkeypatch.setattr(demo_safe, "DEMO_FALLBACK_S", 0.05)


def key(uri="gs://b/jobs/j_1/r_1/e6.jpg"):
    return request_hash("Test question", "MediaCheck", "md5-of-" + uri.rsplit("/", 1)[-1])


async def test_a_fast_live_answer_is_used_and_recorded():
    cache = Cache()
    read, _ = model()
    out = await demo_safe.demo_safe(read, cache, digest)("Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck)
    assert out == LIVE
    assert cache.entries == {key(): LIVE.model_dump(mode="json")}


async def test_a_slow_model_with_a_recorded_answer_returns_after_the_timer():
    read, _ = model(delay_s=1.0)
    start = time.monotonic()
    out = await demo_safe.demo_safe(read, Cache({key(): RECORDED.model_dump(mode="json")}), digest)(
        "Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck
    )
    assert out == RECORDED
    assert time.monotonic() - start < 0.5


async def test_a_slow_model_with_nothing_recorded_returns_the_live_answer():
    read, _ = model(delay_s=0.1)
    out = await demo_safe.demo_safe(read, Cache(), digest)("Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck)
    assert out == LIVE


async def test_a_failing_model_is_answered_from_the_record():
    read, _ = model(fails=True)
    out = await demo_safe.demo_safe(read, Cache({key(): RECORDED.model_dump(mode="json")}), digest)(
        "Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck
    )
    assert out == RECORDED


async def test_a_failing_model_with_nothing_recorded_still_fails_and_records_nothing():
    cache = Cache()
    read, _ = model(fails=True)
    with pytest.raises(TimeoutError):
        await demo_safe.demo_safe(read, cache, digest)("Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck)
    assert cache.entries == {}


async def test_the_artificial_delay_slows_the_model_call():
    read, _ = model()
    start = time.monotonic()
    await demo_safe.demo_safe(read, Cache(), digest, delay_s=0.1)("Test question", "gs://b/x/e6.jpg", MediaCheck)
    assert time.monotonic() - start >= 0.1


def test_the_key_changes_with_the_question_the_schema_or_the_image_and_nothing_else():
    base = request_hash("Test question", "MediaCheck", "md5-a")
    assert base == request_hash("Test question", "MediaCheck", "md5-a")
    assert base != request_hash("Other question", "MediaCheck", "md5-a")
    assert base != request_hash("Test question", "GateCheck", "md5-a")
    assert base != request_hash("Test question", "MediaCheck", "md5-b")


async def test_the_same_image_in_another_jobs_folder_hits_the_same_record():
    read, _ = model(delay_s=1.0)
    cache = Cache({key("gs://b/jobs/j_9/r_4/e6.jpg"): RECORDED.model_dump(mode="json")})
    out = await demo_safe.demo_safe(read, cache, digest)("Test question", "gs://b/jobs/j_1/r_1/e6.jpg", MediaCheck)
    assert out == RECORDED
