"""Offline inventory fixture route for the T10 foundation slice."""

from pathlib import Path

from fastapi import APIRouter

from models.inventory import InventoryListResponse

router = APIRouter(prefix="/api/inventory")
FIXTURE_PATH = Path(__file__).parents[2] / "seed/fixtures/inventory.json"


@router.get("", response_model=InventoryListResponse)
def list_inventory() -> InventoryListResponse:
    return InventoryListResponse.model_validate_json(FIXTURE_PATH.read_text())
