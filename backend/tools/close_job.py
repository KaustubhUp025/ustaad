"""close_job (SPEC §6, T22): a finished job is closed and drafted into a fault card for review, so every closed job
teaches the next one. Pure: the agent wrapper embeds and saves the card and changes his stock."""

from datetime import datetime

from jobs.ingest.cards import present
from jobs.ingest.dedupe import LEVELS
from models.fault_card import FaultCard, FaultCardPart, FaultCardSource
from models.inventory import InventoryDelta
from models.repair import PartUsed, RepairJob
from models.tools import AlreadyClosed, Closed, CloseJobIn, SafetyGateOut
from tools.gates import EVIDENCE, open_gate
from tools.search_fault_cards import canonical_brand

# A card from one job's own account is less sure than a senior's tested fix, and a person reviews it first.
JOB_CARD_CONFIDENCE = 0.7


def close_job(
    inp: CloseJobIn, job: RepairJob, card_id: str, now: datetime
) -> tuple[Closed | AlreadyClosed | SafetyGateOut, RepairJob, FaultCard | None]:
    if job.status == "closed":
        return AlreadyClosed(), job, None
    gate = open_gate(job)
    if gate:
        return SafetyGateOut(gate_id=gate, required_evidence=EVIDENCE[gate]), job, None
    # The photo Ustaad asked for and read; a gate photo carries no findings and only shows the MCB, and a side issue's
    # photo belongs to its own card.
    photo = _photo(job, main=True)
    card = FaultCard(
        **present(
            id=card_id,
            created_at=now,
            photo_uri=photo,
            brand=canonical_brand(inp.brand or ""),
            appliance_type=inp.appliance_type,
            error_code=inp.error_code or "",
            symptom=inp.symptom,
            root_cause=inp.outcome,
            fix_steps=[inp.fix_summary],
            parts=[FaultCardPart(name=p.part) for p in inp.parts_used],
            hazard=max((s.hazard for s in job.steps), key=LEVELS.index, default="none"),
            source=FaultCardSource(type="job", date=now.date().isoformat()),
            confidence=JOB_CARD_CONFIDENCE,
            review_status="needs_review",
        )
    )
    closed = job.model_copy(
        update={"status": "closed", "outcome": inp.outcome, "parts_used": inp.parts_used, "closed_at": now}
    )
    return Closed(card_id=card_id), closed, card


def side_card(inp: CloseJobIn, job: RepairJob, card_id: str, now: datetime) -> FaultCard | None:
    """A side issue he fixed on this job, drafted into its own card for review, tagged with the job's code (S7)."""
    fix = inp.side_fix
    if fix is None:
        return None
    return FaultCard(
        **present(
            id=card_id,
            created_at=now,
            photo_uri=_photo(job, main=False),
            brand=canonical_brand(inp.brand or ""),
            appliance_type=inp.appliance_type,
            error_code="",
            symptom=f"{fix.symptom} (found while fixing {inp.error_code or inp.symptom})",
            root_cause=fix.outcome,
            fix_steps=[fix.fix_summary],
            parts=[],
            hazard="none",
            source=FaultCardSource(type="job", date=now.date().isoformat()),
            confidence=JOB_CARD_CONFIDENCE,
            review_status="needs_review",
        )
    )


def _photo(job: RepairJob, main: bool) -> str | None:
    return next(
        (
            m.uri
            for m in reversed(job.media)
            if m.kind == "photo" and m.findings and (m.reason == "side_issue") != main
        ),
        None,
    )


def stock_deltas(parts: list[PartUsed]) -> list[InventoryDelta]:
    return [InventoryDelta(part=p.part, delta=-p.qty) for p in parts]
