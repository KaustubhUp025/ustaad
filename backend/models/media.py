from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MediaUploadKind = Literal["photo", "video", "import"]
SafeFilename = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"),
]
ContentType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
JobId = Annotated[str, Field(pattern=r"^j_[A-Za-z0-9][A-Za-z0-9_-]*$")]
ImportId = Annotated[str, Field(pattern=r"^i_[A-Za-z0-9][A-Za-z0-9_-]*$")]


class MediaUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MediaUploadKind
    content_type: ContentType
    job_id: JobId | None = None
    import_id: ImportId | None = None
    filename: SafeFilename | None = None


class MediaUploadHeaders(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    content_type: str = Field(alias="Content-Type")
    content_length_range: str = Field(alias="x-goog-content-length-range")


class MediaUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upload_url: str
    uri: str
    expires_in: Literal[900]
    headers: MediaUploadHeaders
