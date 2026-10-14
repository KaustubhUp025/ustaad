import os
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from clients.storage import SignedUpload, StorageUploadClient
from models.media import MediaUploadError, MediaUploadRequest, MediaUploadResponse

UPLOAD_URL_EXPIRES_IN = 900
UPLOAD_RULES = {
    "photo": ({"image/jpeg", "image/png"}, 15_728_640),
    "video": ({"video/mp4"}, 52_428_800),
    "import": (
        {"application/zip", "audio/ogg", "audio/opus", "text/plain", "image/jpeg", "image/png"},
        104_857_600,
    ),
}

router = APIRouter(prefix="/api/media")


class StorageSigner(Protocol):
    def sign_put(self, object_name: str, headers: dict[str, str], expires_in: int) -> SignedUpload: ...


async def get_storage_client() -> StorageUploadClient:
    bucket_name = os.environ.get("MEDIA_BUCKET")
    if not bucket_name:
        raise RuntimeError("MEDIA_BUCKET is required")
    return StorageUploadClient(bucket_name)


def _object_name(request: MediaUploadRequest) -> str:
    prefix = "imports" if request.kind == "import" else "jobs"
    parent_id = request.import_id if request.kind == "import" else request.job_id
    filename = request.filename or "upload"
    leaf = f"{uuid4().hex}-{filename}"
    return "/".join(part for part in (prefix, parent_id, leaf) if part)


@router.post(
    "/upload-url",
    response_model=MediaUploadResponse,
    responses={
        400: {
            "description": "Unsupported content type for upload kind",
            "model": MediaUploadError,
        }
    },
)
async def create_media_upload_url(
    request: MediaUploadRequest,
    storage_client: Annotated[StorageSigner, Depends(get_storage_client)],
) -> MediaUploadResponse:
    allowed_types, maximum_bytes = UPLOAD_RULES[request.kind]
    if request.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="unsupported content type for upload kind")
    headers = {
        "Content-Type": request.content_type,
        "x-goog-content-length-range": f"0,{maximum_bytes}",
    }
    signed = storage_client.sign_put(
        object_name=_object_name(request),
        headers=headers,
        expires_in=UPLOAD_URL_EXPIRES_IN,
    )
    return MediaUploadResponse(
        upload_url=signed.upload_url,
        uri=signed.uri,
        expires_in=UPLOAD_URL_EXPIRES_IN,
        headers=signed.headers,
    )
