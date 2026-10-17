"""Firestore access for the repair tools: a job's repair fields and the fault cards it uses (firestore.md)."""

from collections.abc import Callable
from typing import ClassVar

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from models.fault_card import FaultCard
from models.inventory import InventoryItem
from models.repair import RepairJob
from models.worker import Worker

REPAIR_FIELDS = {"steps", "gates", "current_step", "media", "status", "outcome", "parts_used", "closed_at", "translation_lang"}
DISTANCE = "distance"


def _fault_card(cid: str, data: dict) -> FaultCard:
    # `embedding` is server-only and not part of the public card; `distance` comes back from a vector query.
    return FaultCard.model_validate({"id": cid} | {k: v for k, v in data.items() if k not in ("embedding", DISTANCE)})


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
        return [_fault_card(cid, found[cid]) for cid in card_ids]


class CardStore:
    """`fault_cards` with their 768-dim embedding, for the import's dedupe and search_fault_cards."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def nearest(self, brand: str, vector: list[float], limit: int) -> list[tuple[FaultCard, float]]:
        """The brand's `limit` nearest cards with their cosine similarity (1 = same direction)."""
        query = (
            self._db.collection("fault_cards")
            .where(filter=FieldFilter("brand", "==", brand))
            .find_nearest(
                vector_field="embedding",
                query_vector=Vector(vector),
                limit=limit,
                distance_measure=DistanceMeasure.COSINE,
                distance_result_field=DISTANCE,
            )
        )
        return [(_fault_card(doc.id, doc.to_dict()), 1 - doc.get(DISTANCE)) for doc in query.get()]

    def save(self, card: FaultCard, vector: list[float]) -> None:
        data = {k: v for k, v in card.to_public_dict().items() if k != "id"}
        self._db.collection("fault_cards").document(card.id).set(data | {"embedding": Vector(vector)})


class ImportStore:
    """Contracted lifecycle fields for `imports/{id}`."""

    ALLOWED_FIELDS: ClassVar[set[str]] = {
        "status",
        "files_total",
        "audio_total",
        "audio_done",
        "threads",
        "cards_created",
        "cards_needing_review",
        "errors",
        "started_at",
        "finished_at",
    }

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def load(self, import_id: str) -> dict | None:
        snapshot = self._db.collection("imports").document(import_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        return {"status": data.get("status"), "errors": data.get("errors", [])}

    def update(self, import_id: str, **fields) -> None:
        if not fields.keys() <= self.ALLOWED_FIELDS:
            raise ValueError("unsupported import fields")
        self._db.collection("imports").document(import_id).set(fields, merge=True)


def _inventory_item(snapshot: firestore.DocumentSnapshot) -> InventoryItem:
    data = snapshot.to_dict() or {}
    # firestore.md: the entity's id is the document ID; a stored id that disagrees is a broken document.
    if data.get("id", snapshot.id) != snapshot.id:
        raise ValueError(f"inventory document {snapshot.id} holds another id")
    return InventoryItem.model_validate(data | {"id": snapshot.id})


class InventoryStore:
    """`workers/{wid}/inventory/{part_id}`."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _parts(self, worker_id: str) -> firestore.CollectionReference:
        return self._db.collection("workers").document(worker_id).collection("inventory")

    def items(self, worker_id: str) -> list[InventoryItem]:
        return [_inventory_item(doc) for doc in self._parts(worker_id).stream()]

    def update[T](
        self, worker_id: str, change: Callable[[list[InventoryItem]], tuple[T, list[InventoryItem]]]
    ) -> T:
        """Runs `change` on his stock in a transaction, so two quick updates cannot both start from the same qty;
        `change` returns its result and the parts it changed."""
        parts = self._parts(worker_id)

        @firestore.transactional
        def run(tx: firestore.Transaction) -> T:
            out, changed = change([_inventory_item(doc) for doc in parts.stream(transaction=tx)])
            for item in changed:
                tx.set(parts.document(item.id), item.model_dump(mode="json", exclude={"id"}))
            return out

        return run(self._db.transaction())


class DemoCacheStore:
    """`demo_cache/{hash}`: real model answers recorded for the demo-safe fallback (app/demo_safe.py)."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def get(self, key: str) -> dict | None:
        doc = self._db.collection("demo_cache").document(key).get()
        return doc.to_dict()["response"] if doc.exists else None

    def put(self, key: str, response: dict, model: str) -> None:
        self._db.collection("demo_cache").document(key).set(
            {"request_hash": key, "response": response, "model": model, "created_at": firestore.SERVER_TIMESTAMP}
        )


class WorkerStore:
    """`workers/{wid}`."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def get(self, worker_id: str) -> Worker | None:
        doc = self._db.collection("workers").document(worker_id).get()
        return Worker.model_validate(doc.to_dict() | {"id": worker_id}) if doc.exists else None
