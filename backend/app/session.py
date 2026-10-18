"""Signed demo session tokens (rest.md: "a signed, 24 h demo token"): the worker id and an expiry, signed with
SESSION_SECRET (HMAC-SHA256). There is no login; a token only ever names a seeded demo worker."""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

TOKEN_TTL = timedelta(hours=24)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(os.environ["SESSION_SECRET"].encode(), payload.encode(), hashlib.sha256).digest())


def issue(worker_id: str, now: datetime) -> str:
    # The nonce makes each visit's token its own, even for one worker in the same second: memory is kept per token.
    claims = {"wid": worker_id, "exp": int((now + TOKEN_TTL).timestamp()), "nonce": secrets.token_hex(8)}
    payload = _b64(json.dumps(claims).encode())
    return f"{payload}.{_sign(payload)}"


def verify(token: str, now: datetime) -> str | None:
    """The token's worker id, or None if it is malformed, tampered with, signed with another secret or expired."""
    payload, _, sig = token.partition(".")
    if not sig or not hmac.compare_digest(sig, _sign(payload)):
        return None
    claims = json.loads(_unb64(payload))
    return claims["wid"] if now.timestamp() < claims["exp"] else None


# Declares the bearer scheme in OpenAPI; auto_error is off so a missing token gets the contract's 401, not 403.
BEARER = HTTPBearer(auto_error=False)


def require_session(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)]) -> str:
    """FastAPI dependency: the worker id of a valid `Authorization: Bearer <token>`, else 401 (rest.md)."""
    worker_id = verify(credentials.credentials, datetime.now(UTC)) if credentials else None
    if worker_id is None:
        raise HTTPException(401)
    return worker_id
