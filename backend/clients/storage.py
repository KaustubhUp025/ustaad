from dataclasses import dataclass
from datetime import timedelta

import google.auth
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import storage


@dataclass(frozen=True)
class SignedUpload:
    upload_url: str
    uri: str
    headers: dict[str, str]


class StorageUploadClient:
    def __init__(
        self,
        bucket_name: str,
        client: storage.Client | None = None,
        credentials: Credentials | None = None,
        auth_request: Request | None = None,
    ) -> None:
        project = None
        if credentials is None:
            credentials, project = google.auth.default()
        self._bucket_name = bucket_name
        self._credentials = credentials
        self._auth_request = auth_request or Request()
        self._client = client or storage.Client(project=project, credentials=credentials)

    def sign_put(self, object_name: str, headers: dict[str, str], expires_in: int) -> SignedUpload:
        self._credentials.refresh(self._auth_request)
        blob = self._client.bucket(self._bucket_name).blob(object_name)
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="PUT",
            headers=headers,
            service_account_email=self._credentials.service_account_email,
            access_token=self._credentials.token,
        )
        return SignedUpload(
            upload_url=upload_url,
            uri=f"gs://{self._bucket_name}/{object_name}",
            headers=dict(headers),
        )
