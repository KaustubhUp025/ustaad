"""GET /api/fault-cards (rest.md): authenticated, filtered group knowledge cards."""

import os
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.session import require_session
from clients.firestore import CardStore
from models.fault_card import FaultCard, FaultCardListResponse, ReviewStatus
from models.repair import ApplianceType

router = APIRouter(prefix="/api/fault-cards")


@cache
def card_store() -> CardStore:
    return CardStore(firestore.Client(database=os.environ["FIRESTORE_DB"]))


Store = Annotated[CardStore, Depends(card_store)]
WorkerId = Annotated[str, Depends(require_session)]


def _contains(card: FaultCard, query: str) -> bool:
    fields = (card.brand, card.model, card.series, card.error_code, card.symptom, card.root_cause)
    return any(query in field.casefold() for field in fields if field)


@router.get("", response_model=FaultCardListResponse)
def list_fault_cards(
    store: Store,
    worker_id: WorkerId,
    q: str | None = None,
    brand: str | None = None,
    code: str | None = None,
    status: ReviewStatus | None = None,
    appliance_type: ApplianceType | None = None,
) -> FaultCardListResponse:
    del worker_id
    cards = store.list()
    if q:
        cards = [card for card in cards if _contains(card, q.casefold())]
    if brand:
        cards = [card for card in cards if card.brand.casefold() == brand.casefold()]
    if code:
        cards = [card for card in cards if card.error_code.casefold() == code.casefold()]
    if status:
        cards = [card for card in cards if card.review_status == status]
    if appliance_type:
        cards = [card for card in cards if card.appliance_type == appliance_type]
    return FaultCardListResponse(items=cards, next=None)
