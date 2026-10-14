import httpx
import pytest
from fastapi import HTTPException

from app.main import app
from app.media import get_storage_client


class UnusedStorageClient:
    def sign_put(self, object_name, headers, expires_in):
        raise AssertionError("invalid requests must not reach Storage")


@pytest.fixture(autouse=True)
def fake_storage():
    async def override_storage_client():
        return UnusedStorageClient()

    app.dependency_overrides[get_storage_client] = override_storage_client
    yield
    app.dependency_overrides.clear()


@app.get("/api/_test/http-error/{status_code}", include_in_schema=False)
async def raise_http_error(status_code: int):
    raise HTTPException(
        status_code=status_code,
        detail="job j_private_4821 failed with caller-supplied text",
    )


@app.get("/api/_test/internal-error", include_in_schema=False)
async def raise_internal_error():
    raise RuntimeError("credential=must-not-leak")


async def request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def test_invalid_media_type_uses_error_envelope():
    response = await request(
        "POST",
        "/api/media/upload-url",
        json={"kind": "photo", "content_type": "video/mp4"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Bad request",
        }
    }


async def test_malformed_media_request_uses_safe_validation_envelope():
    response = await request(
        "POST",
        "/api/media/upload-url",
        json={"kind": "photo", "content_type": "image/jpeg", "filename": "../secret"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "validation_error", "message": "Request validation failed"}
    }


@pytest.mark.parametrize(
    ("status_code", "code", "message"),
    [
        (400, "bad_request", "Bad request"),
        (401, "unauthorized", "Authentication required"),
        (403, "forbidden", "Forbidden"),
        (404, "not_found", "Not found"),
        (409, "conflict", "Conflict"),
        (422, "validation_error", "Request validation failed"),
        (429, "rate_limited", "Too many requests"),
        (500, "internal_error", "Internal server error"),
        (418, "http_error", "Request failed"),
    ],
)
async def test_route_http_exception_uses_fixed_safe_envelope(status_code, code, message):
    response = await request("GET", f"/api/_test/http-error/{status_code}")

    assert response.status_code == status_code
    assert response.json() == {
        "error": {"code": code, "message": message}
    }
    assert "j_private_4821" not in response.text
    assert "caller-supplied" not in response.text


async def test_unexpected_exception_uses_safe_internal_envelope():
    response = await request("GET", "/api/_test/internal-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    assert "credential" not in response.text
    assert "traceback" not in response.text.lower()


async def test_healthz_behavior_is_unchanged(monkeypatch):
    monkeypatch.setenv("FLASH_MODEL", "test-flash")
    monkeypatch.setenv("LIVE_MODEL", "test-live")

    response = await request("GET", "/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "flash_model": "test-flash",
        "live_model": "test-live",
        "demo_safe": False,
    }
