import re
from datetime import timedelta

import httpx
import pytest

from app.main import app
from app.media import get_storage_client
from clients.storage import SignedUpload, StorageUploadClient

ALLOWED_UPLOADS = [
    ("photo", "image/jpeg", 15_728_640),
    ("photo", "image/png", 15_728_640),
    ("video", "video/mp4", 52_428_800),
    ("import", "application/zip", 104_857_600),
    ("import", "audio/ogg", 104_857_600),
    ("import", "audio/opus", 104_857_600),
    ("import", "text/plain", 104_857_600),
    ("import", "image/jpeg", 104_857_600),
    ("import", "image/png", 104_857_600),
]
ALL_CONTENT_TYPES = {content_type for _, content_type, _ in ALLOWED_UPLOADS}
REJECTED_UPLOADS = [
    (kind, content_type)
    for kind in ("photo", "video", "import")
    for content_type in ALL_CONTENT_TYPES
    if not any(
        allowed_kind == kind and allowed_type == content_type
        for allowed_kind, allowed_type, _ in ALLOWED_UPLOADS
    )
]


class FakeStorageClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str], int]] = []

    def sign_put(self, object_name: str, headers: dict[str, str], expires_in: int) -> SignedUpload:
        self.calls.append((object_name, headers, expires_in))
        return SignedUpload(
            upload_url=f"https://uploads.example/{object_name}",
            uri=f"gs://test-media/{object_name}",
            headers=headers,
        )


async def post_upload(payload: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/media/upload-url", json=payload)


@pytest.fixture
def fake_storage() -> FakeStorageClient:
    fake = FakeStorageClient()

    async def override_storage_client():
        return fake

    app.dependency_overrides[get_storage_client] = override_storage_client
    yield fake
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("kind", "content_type", "maximum_bytes"),
    ALLOWED_UPLOADS,
)
async def test_upload_url_allows_each_kind_content_type_pair(
    fake_storage, kind, content_type, maximum_bytes
):
    id_field = "import_id" if kind == "import" else "job_id"
    parent_id = "i_1" if kind == "import" else "j_1"
    prefix = "imports/i_1" if kind == "import" else "jobs/j_1"
    payload = {"kind": kind, "content_type": content_type, id_field: parent_id, "filename": "upload.bin"}

    response = await post_upload(payload)

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 900
    assert re.fullmatch(rf"{prefix}/[0-9a-f]{{32}}-upload\.bin", fake_storage.calls[0][0])
    expected_headers = {
        "Content-Type": content_type,
        "x-goog-content-length-range": f"0,{maximum_bytes}",
    }
    assert fake_storage.calls[0][1:] == (expected_headers, 900)
    assert body == {
        "upload_url": f"https://uploads.example/{fake_storage.calls[0][0]}",
        "uri": f"gs://test-media/{fake_storage.calls[0][0]}",
        "expires_in": 900,
        "headers": expected_headers,
    }


async def test_upload_url_without_id_stays_in_kind_prefix(fake_storage):
    response = await post_upload({"kind": "photo", "content_type": "image/png"})

    assert response.status_code == 200
    assert re.fullmatch(r"jobs/[0-9a-f]{32}-upload", fake_storage.calls[0][0])


async def test_upload_url_rejects_invalid_kind(fake_storage):
    response = await post_upload({"kind": "document", "content_type": "image/jpeg"})

    assert response.status_code == 422
    assert fake_storage.calls == []


@pytest.mark.parametrize(
    ("kind", "content_type"),
    REJECTED_UPLOADS
    + [
        ("photo", "application/pdf"),
        ("video", "application/pdf"),
        ("import", "application/pdf"),
    ],
)
async def test_upload_url_rejects_unsupported_or_wrong_kind_content_type(
    fake_storage, kind, content_type
):
    response = await post_upload({"kind": kind, "content_type": content_type})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Bad request",
        }
    }
    assert fake_storage.calls == []


@pytest.mark.parametrize("filename", ["../secret", "/absolute.jpg", "nested/photo.jpg", r"nested\photo.jpg", ".", "..", ""])
async def test_upload_url_rejects_unsafe_filename(fake_storage, filename):
    response = await post_upload(
        {"kind": "photo", "content_type": "image/jpeg", "filename": filename}
    )

    assert response.status_code == 422
    assert fake_storage.calls == []


@pytest.mark.parametrize(
    ("kind", "id_field", "unsafe_id"),
    [
        ("photo", "job_id", "../j_1"),
        ("video", "job_id", "j_1/../../escape"),
        ("photo", "job_id", r"j_1\escape"),
        ("photo", "job_id", "i_wrong_prefix"),
        ("import", "import_id", "../i_1"),
        ("import", "import_id", "i_1/../../escape"),
        ("import", "import_id", r"i_1\escape"),
        ("import", "import_id", "j_wrong_prefix"),
    ],
)
async def test_upload_url_rejects_unsafe_or_wrong_prefix_ids(
    fake_storage, kind, id_field, unsafe_id
):
    response = await post_upload(
        {"kind": kind, "content_type": "application/zip" if kind == "import" else "image/jpeg", id_field: unsafe_id}
    )

    assert response.status_code == 422
    assert fake_storage.calls == []


async def test_route_uses_fake_without_creating_google_client(fake_storage, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("external Storage client was created")

    monkeypatch.setattr("clients.storage.storage.Client", fail_if_called)

    response = await post_upload({"kind": "photo", "content_type": "image/jpeg"})

    assert response.status_code == 200


def test_storage_client_signs_a_v4_put_for_exact_expiry():
    class FakeCredentials:
        service_account_email = "ustaad-run@example.invalid"
        token = "test-access-token"

        def __init__(self) -> None:
            self.refresh_calls = []

        def refresh(self, request) -> None:
            self.refresh_calls.append(request)

    class FakeBlob:
        def __init__(self) -> None:
            self.kwargs = None

        def generate_signed_url(self, **kwargs):
            self.kwargs = {**kwargs, "headers": dict(kwargs["headers"])}
            kwargs["headers"]["Host"] = "storage.googleapis.com"
            return "https://storage.example/signed"

    class FakeBucket:
        def __init__(self, blob: FakeBlob) -> None:
            self._blob = blob

        def blob(self, object_name: str):
            assert object_name == "jobs/j_1/random-panel.jpg"
            return self._blob

    class FakeGoogleClient:
        def __init__(self, blob: FakeBlob) -> None:
            self._blob = blob

        def bucket(self, bucket_name: str):
            assert bucket_name == "media-bucket"
            return FakeBucket(self._blob)

    blob = FakeBlob()
    credentials = FakeCredentials()
    auth_request = object()
    client = StorageUploadClient(
        "media-bucket",
        client=FakeGoogleClient(blob),
        credentials=credentials,
        auth_request=auth_request,
    )
    required_headers = {
        "Content-Type": "image/jpeg",
        "x-goog-content-length-range": "0,15728640",
    }
    expected_headers = dict(required_headers)

    result = client.sign_put("jobs/j_1/random-panel.jpg", required_headers, 900)

    assert result == SignedUpload(
        upload_url="https://storage.example/signed",
        uri="gs://media-bucket/jobs/j_1/random-panel.jpg",
        headers=expected_headers,
    )
    assert required_headers == expected_headers
    assert credentials.refresh_calls == [auth_request]
    assert blob.kwargs == {
        "version": "v4",
        "expiration": timedelta(seconds=900),
        "method": "PUT",
        "headers": expected_headers,
        "service_account_email": "ustaad-run@example.invalid",
        "access_token": "test-access-token",
    }
