from typing import Literal

from pydantic import BaseModel, ConfigDict

ErrorCode = Literal[
    "bad_request",
    "unauthorized",
    "forbidden",
    "not_found",
    "conflict",
    "validation_error",
    "rate_limited",
    "internal_error",
    "http_error",
]


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
