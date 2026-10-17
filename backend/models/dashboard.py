"""The documented aggregate response for the owner dashboard."""

from typing import Annotated

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    cards: Annotated[int, Field(strict=True, ge=0)]
    cards_needing_review: Annotated[int, Field(strict=True, ge=0)]
    jobs_7d: Annotated[int, Field(strict=True, ge=0)]
    imports: Annotated[int, Field(strict=True, ge=0)]
