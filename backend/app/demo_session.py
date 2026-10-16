"""POST /api/demo/session (rest.md): "Try the demo" with no login. A judge gets a signed 24 h token for a seeded demo
worker; a worker that is not marked demo is never handed out."""

import os
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from google.cloud import firestore

from app.session import issue
from clients.firestore import WorkerStore
from models.worker import DemoSessionRequest, DemoSessionResponse

router = APIRouter(prefix="/api/demo")


@cache
def worker_store() -> WorkerStore:
    return WorkerStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


@router.post("/session", response_model=DemoSessionResponse)
def demo_session(
    request: Request,
    store: Annotated[WorkerStore, Depends(worker_store)],
    body: Annotated[DemoSessionRequest | None, Body()] = None,
) -> DemoSessionResponse:
    worker = store.get((body or DemoSessionRequest()).worker_id)
    if worker is None or not worker.demo:
        raise HTTPException(404)
    ws_url = str(request.base_url).replace("http", "ws", 1) + "ws/live"
    return DemoSessionResponse(token=issue(worker.id, datetime.now(UTC)), worker=worker, ws_url=ws_url)
