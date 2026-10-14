from dataclasses import dataclass
from datetime import timedelta

from google.cloud import storage


@dataclass(frozen=True)
class SignedUpload:
    upload_url: str
    uri: str
    headers: dict[str, str]


class StorageUploadClient:
    def __init__(self, bucket_name: str, client: storage.Client | None = None) -> None:
        self._bucket_name = bucket_name
        self._client = client or storage.Client()

    def sign_put(self, object_name: str, headers: dict[str, str], expires_in: int) -> SignedUpload:
        blob = self._client.bucket(self._bucket_name).blob(object_name)
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="PUT",
            headers=headers,
        )
        return SignedUpload(
            upload_url=upload_url,
            uri=f"gs://{self._bucket_name}/{object_name}",
            headers=dict(headers),
        )
