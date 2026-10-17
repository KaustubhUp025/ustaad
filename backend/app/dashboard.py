"""GET /api/dashboard/summary (rest.md): authenticated dashboard counts."""

import os
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.session import require_session
from clients.firestore import DashboardStore
from models.dashboard import DashboardSummary

router = APIRouter(prefix="/api/dashboard")


@cache
def dashboard_store() -> DashboardStore:
    return DashboardStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


Store = Annotated[DashboardStore, Depends(dashboard_store)]
WorkerId = Annotated[str, Depends(require_session)]


@router.get("/summary", response_model=DashboardSummary)
def get_summary(store: Store, worker_id: WorkerId) -> DashboardSummary:
    return store.summary(worker_id, datetime.now(UTC))
