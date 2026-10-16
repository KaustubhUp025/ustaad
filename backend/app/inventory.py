"""GET / PATCH /api/inventory (rest.md): his stock, and stock deltas applied all or nothing."""

import os
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from clients.firestore import InventoryStore
from models.inventory import InventoryDeltaRequest, InventoryListResponse
from tools.inventory import StockError, apply_deltas

router = APIRouter(prefix="/api/inventory")
# Until demo sessions (T27) say who is calling, every request is the default demo worker (rest.md).
DEMO_WORKER_ID = "w_hi_demo"


@cache
def inventory_store() -> InventoryStore:
    return InventoryStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


Store = Annotated[InventoryStore, Depends(inventory_store)]


@router.get("", response_model=InventoryListResponse)
def list_inventory(store: Store) -> InventoryListResponse:
    return InventoryListResponse(items=store.items(DEMO_WORKER_ID))


@router.patch("", response_model=InventoryListResponse)
def update_inventory(body: InventoryDeltaRequest, store: Store) -> InventoryListResponse:
    now = datetime.now(UTC)
    try:
        store.update(DEMO_WORKER_ID, lambda items: (None, apply_deltas(items, body.deltas, "manual", now)))
    except StockError as err:
        raise HTTPException(404 if err.reason == "unknown_part" else 409) from err
    return InventoryListResponse(items=store.items(DEMO_WORKER_ID))
