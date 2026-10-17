"""A shop as Places API (New) text search returns it, the fields find_vendors reads."""

from pydantic import BaseModel

from models.worker import Geo


class Place(BaseModel):
    id: str
    name: str
    address: str | None
    geo: Geo | None
