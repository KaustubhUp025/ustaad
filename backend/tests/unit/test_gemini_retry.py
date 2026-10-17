"""The import's Flash and embedding calls retry Vertex's transient 429s (Oct 17 dev import: 8 of 19 attachments,
the thread grouping and threads were lost to single 429s). Gemini itself is faked: only the client's options are read."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from clients import gemini


class Answer(BaseModel):
    ok: bool


MADE: list[dict] = []


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


def retries(kwargs: dict) -> bool:
    options = kwargs.get("http_options")
    # The SDK's defaults (5 attempts, exponential backoff) retry 408, 429 and 5xx (google.genai._api_client).
    return options is not None and options.retry_options is not None


async def test_import_calls_retry_transient_errors(tmp_path: Path):
    media = tmp_path / "m.flac"
    media.write_bytes(b"synthetic")
    await gemini.ask_json("q", Answer)
    await gemini.transcribe_import_audio(media)
    await gemini.describe_import_photo(media)
    gemini.embed(["t"], "RETRIEVAL_DOCUMENT")

    assert len(MADE) == 4
    assert all(retries(kwargs) for kwargs in MADE)
