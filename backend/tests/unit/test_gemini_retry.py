"""The WhatsApp import's Gemini calls retry Vertex 429s and hung calls (Oct 17 dev imports lost attachments, the thread
grouping and threads to both); a worker's live search embedding fails fast. Gemini is faked: only client options are read."""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from google.genai import _api_client, errors
from pydantic import BaseModel

from clients import gemini
from jobs.ingest import job

MADE: list[dict] = []


class Answer(BaseModel):
    ok: bool


class FakeClient:
    def __init__(self, **kwargs) -> None:
        MADE.append(kwargs)

        async def generate_content(**_):
            return SimpleNamespace(text='{"ok": true}')

        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        self.models = SimpleNamespace(embed_content=lambda **_: SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1])]))


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    MADE.clear()
    monkeypatch.setattr(gemini.genai, "Client", FakeClient)
    monkeypatch.setenv("FLASH_MODEL", "flash-test")
    monkeypatch.setenv("EMBED_MODEL", "embed-test")
    monkeypatch.setenv("EMBED_DIM", "1")


def import_policy(kwargs: dict) -> bool:
    options = kwargs["http_options"]
    return options.timeout == 120_000 and options.retry_options is not None


async def test_import_media_calls_use_the_120_s_retrying_policy(tmp_path: Path):
    media = tmp_path / "m.flac"
    media.write_bytes(b"synthetic")
    await gemini.transcribe_import_audio(media)
    await gemini.describe_import_photo(media)

    assert len(MADE) == 2
    assert all(import_policy(kwargs) for kwargs in MADE)


async def test_import_job_wires_grouping_extraction_and_embedding_to_the_import_policy(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(job.firestore, "Client", lambda **_: object())
    monkeypatch.setattr(job, "ImportStorageClient", lambda bucket: object())
    deps = job._concrete_dependencies("(default)", "bucket", tmp_path)

    await deps.ask("q", Answer)
    await deps.thread_client._ask("q", Answer)
    deps.embed(["t"], "RETRIEVAL_DOCUMENT")

    assert len(MADE) == 3
    assert all(import_policy(kwargs) for kwargs in MADE)


async def test_live_search_embedding_fails_fast_and_other_ask_json_callers_are_unchanged():
    gemini.embed(["t"], "RETRIEVAL_QUERY")
    await gemini.ask_json("q", Answer)

    live, ask = MADE
    assert live["http_options"].timeout == 10_000
    assert live["http_options"].retry_options is None
    assert ask["http_options"] is None


def test_the_sdk_retries_429_and_timeouts_with_the_import_options_but_not_400():
    # The installed SDK's own rule (google.genai._api_client.retry_args), so an upgrade that changes it fails here.
    rule = _api_client.retry_args(gemini.IMPORT_CALLS.retry_options)
    exhausted = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "busy"}})
    invalid = errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad"}})

    assert rule["retry"].predicate(exhausted)
    assert rule["retry"].predicate(httpx.ReadTimeout("hung"))
    assert not rule["retry"].predicate(invalid)
    assert rule["stop"].max_attempt_number == 5


def test_the_live_search_embedding_goes_to_embed_location_when_set(monkeypatch):
    # Oct 18, from the laptop: `global` took 12.6 s for a while (past the 10 s timeout), then 2.5 s; asia-south1 took
    # 1.0-1.4 s throughout, with identical vectors (cosine 1.0), so stored cards still match.
    monkeypatch.setenv("EMBED_LOCATION", "asia-south1")
    gemini.embed(["t"], "RETRIEVAL_QUERY")
    monkeypatch.delenv("EMBED_LOCATION")
    gemini.embed(["t"], "RETRIEVAL_QUERY")

    regional, default = MADE
    assert regional["location"] == "asia-south1"
    assert default["location"] is None
