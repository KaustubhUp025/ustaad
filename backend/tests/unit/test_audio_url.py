"""POST /api/media/audio-url (rest.md): a signed GET URL for a fault card source's voice note, so the G2 source chip
can play it; nothing else in the bucket is ever signed, and a session token is required."""

from datetime import UTC, datetime

import httpx
import pytest

from app.main import app
from app.media import get_storage_client
from app.session import issue

VOICE_NOTE = "gs://test-media/imports/i_ab12/derived/i_ab12:m3.flac"


class FakeSigner:
    bucket_name = "test-media"

    def __init__(self) -> None:
        self.signed: list[tuple[str, int]] = []

    def sign_get(self, object_name: str, expires_in: int) -> str:
        self.signed.append((object_name, expires_in))
        return f"https://downloads.example/{object_name}?sig=x"


@pytest.fixture
def signer():
    fake = FakeSigner()

    async def override():
        return fake

    app.dependency_overrides[get_storage_client] = override
    yield fake
    app.dependency_overrides.clear()


async def post(uri: str, token: str | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/media/audio-url", json={"uri": uri}, headers=headers)


def token() -> str:
    return issue("w_hi_demo", datetime.now(UTC))


async def test_a_source_voice_note_gets_a_signed_get_url(signer):
    response = await post(VOICE_NOTE, token())
    assert response.status_code == 200
    assert response.json() == {
        "url": "https://downloads.example/imports/i_ab12/derived/i_ab12:m3.flac?sig=x",
        "expires_in": 900,
    }
    assert signer.signed == [("imports/i_ab12/derived/i_ab12:m3.flac", 900)]


@pytest.mark.parametrize("bad_token", [None, "", "demo", "a.b"])
async def test_without_a_valid_session_token_it_is_unauthorized(signer, bad_token):
    response = await post(VOICE_NOTE, bad_token)
    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthorized")
    assert signer.signed == []


@pytest.mark.parametrize(
    "uri",
    [
        "gs://other-bucket/imports/i_ab12/derived/i_ab12:m3.flac",
        "gs://test-media/jobs/j_1/r_1/photo.jpg",
        "gs://test-media/imports/i_ab12/export.zip",
        "gs://test-media/imports/i_ab12/derived/note.opus",
        "gs://test-media/imports/i_ab12/derived/../../jobs/j_1/r_1/x.flac",
        "gs://test-media/imports/i_ab12/derived/sub/x.flac",
        "https://test-media/imports/i_ab12/derived/x.flac",
    ],
)
async def test_anything_but_a_source_voice_note_is_not_found(signer, uri):
    # The route exists and signs a real voice note, so the 404 below is the refusal, not a missing route.
    assert (await post(VOICE_NOTE, token())).status_code == 200
    response = await post(uri, token())
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")
    assert len(signer.signed) == 1


def test_openapi_requires_the_bearer_token_on_audio_url():
    spec = app.openapi()
    operation = spec["paths"]["/api/media/audio-url"]["post"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert spec["components"]["securitySchemes"]["HTTPBearer"] == {"type": "http", "scheme": "bearer"}
    assert all(p["name"].lower() != "authorization" for p in operation.get("parameters", []))
