"""Firestore access for the repair tools: a job's repair fields and the fault cards it uses (firestore.md)."""

from collections.abc import Callable

from google.cloud import firestore

from models.fault_card import FaultCard
from models.repair import RepairJob

REPAIR_FIELDS = {"steps", "gates", "current_step", "media"}


def _job(snapshot: firestore.DocumentSnapshot, job_id: str) -> RepairJob:
    data = snapshot.to_dict() or {}
    return RepairJob(job_id=job_id, **{k: v for k, v in data.items() if k in REPAIR_FIELDS})


class JobStore:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def load(self, job_id: str) -> RepairJob:
        """A job with no repair started yet loads with no steps and all gates open."""
        return _job(self._db.collection("jobs").document(job_id).get(), job_id)

    def update[T](self, job_id: str, change: Callable[[RepairJob], tuple[T, RepairJob]]) -> T:
        """Runs `change` on the job in a transaction, so two quick calls cannot both hand out the same step."""
        ref = self._db.collection("jobs").document(job_id)

        @firestore.transactional
        def run(tx: firestore.Transaction) -> T:
            out, job = change(_job(ref.get(transaction=tx), job_id))
            tx.set(ref, job.model_dump(mode="json", include=REPAIR_FIELDS), merge=True)
            return out

        return run(self._db.transaction())

    def fault_cards(self, card_ids: list[str]) -> list[FaultCard]:
        refs = [self._db.collection("fault_cards").document(cid) for cid in card_ids]
        found = {doc.id: doc.to_dict() for doc in self._db.get_all(refs)}
        # `embedding` is server-only and not part of the public card.
        return [
            FaultCard.model_validate({"id": cid} | {k: v for k, v in found[cid].items() if k != "embedding"})
            for cid in card_ids
        ]
