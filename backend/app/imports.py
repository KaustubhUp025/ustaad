"""GET /api/imports/{id} (rest.md): an authenticated worker's import lifecycle."""

import os
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.session import require_session
from clients.firestore import ImportStore
from models.imports import Import, ImportListResponse

router = APIRouter(prefix="/api/imports")


@cache
def import_store() -> ImportStore:
    return ImportStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


Store = Annotated[ImportStore, Depends(import_store)]
WorkerId = Annotated[str, Depends(require_session)]


@router.get("", response_model=ImportListResponse)
def list_imports(store: Store, worker_id: WorkerId) -> ImportListResponse:
    return ImportListResponse(items=store.list(worker_id))


@router.get("/{import_id}", response_model=Import)
def get_import(import_id: str, store: Store, worker_id: WorkerId) -> Import:
    record = store.get(import_id)
    if record is None or record.worker_id != worker_id:
        raise HTTPException(404)
    return record
