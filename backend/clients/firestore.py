"""Firestore access for the repair tools: a job's repair fields and the fault cards it uses (firestore.md)."""

from collections.abc import Callable
from datetime import datetime
from typing import ClassVar

from google.api_core.exceptions import Conflict
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from models.fault_card import FaultCard
from models.inventory import InventoryItem
from models.quotes import QuoteDoc, QuoteRequest, Vendor
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


class QuoteStore:
    """`quote_requests/{qrid}` with their `quotes`, the worker's `vendors`, and `tg_updates` for webhook dedupe.
    Only requests younger than their expiry are searched, so the scan stays the size of the last 30 minutes."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _quotes(self, qrid: str) -> firestore.CollectionReference:
        return self._db.collection("quote_requests").document(qrid).collection("quotes")

    def vendors(self, worker_id: str) -> list[Vendor]:
        docs = self._db.collection("workers").document(worker_id).collection("vendors").stream()
        return [Vendor(id=doc.id, name=doc.get("name"), tg_chat_id=doc.get("tg_chat_id")) for doc in docs]

    def create(self, request: QuoteRequest, docs: list[QuoteDoc]) -> None:
        batch = self._db.batch()
        batch.set(
            self._db.collection("quote_requests").document(request.id), request.model_dump(exclude={"id"})
        )
        for quote in docs:
            batch.set(self._quotes(request.id).document(quote.id), quote.model_dump(exclude={"id"}))
        batch.commit()

    def get(self, qrid: str) -> tuple[QuoteRequest, list[QuoteDoc]] | None:
        doc = self._db.collection("quote_requests").document(qrid).get()
        if not doc.exists:
            return None
        quotes = [QuoteDoc.model_validate(q.to_dict() | {"id": q.id}) for q in self._quotes(qrid).stream()]
        return QuoteRequest.model_validate(doc.to_dict() | {"id": qrid}), quotes

    def _unexpired(self, now: datetime) -> list[QuoteRequest]:
        query = self._db.collection("quote_requests").where(filter=FieldFilter("expires_at", ">", now))
        return [QuoteRequest.model_validate(doc.to_dict() | {"id": doc.id}) for doc in query.stream()]

    def find(self, qid: str, now: datetime) -> tuple[QuoteRequest, QuoteDoc] | None:
        """The quote and its request, if the request has not expired."""
        for request in self._unexpired(now):
            doc = self._quotes(request.id).document(qid).get()
            if doc.exists:
                return request, QuoteDoc.model_validate(doc.to_dict() | {"id": qid})
        return None

    def open_for_chat(self, chat_id: int, now: datetime) -> list[tuple[QuoteRequest, QuoteDoc]]:
        """Every quote sent to this Telegram chat in a request that is still open."""
        return [
            (request, QuoteDoc.model_validate(doc.to_dict() | {"id": doc.id}))
            for request in self._unexpired(now)
            if request.status == "open"
            for doc in self._quotes(request.id)
            .where(filter=FieldFilter("tg_chat_id", "==", chat_id))
            .stream()
        ]

    def update_quote(self, qrid: str, qid: str, change: Callable[[QuoteDoc], QuoteDoc]) -> QuoteDoc:
        """Runs `change` on the stored quote in a transaction, so a tap and a reply cannot both start from the same
        state."""
        ref = self._quotes(qrid).document(qid)

        @firestore.transactional
        def run(tx: firestore.Transaction) -> QuoteDoc:
            quote = change(QuoteDoc.model_validate(ref.get(transaction=tx).to_dict() | {"id": qid}))
            tx.set(ref, quote.model_dump(exclude={"id"}))
            return quote

        return run(self._db.transaction())

    def approve(
        self, qrid: str, qid: str, change: Callable[[QuoteRequest, QuoteDoc], tuple[QuoteRequest, QuoteDoc]]
    ) -> tuple[QuoteRequest, QuoteDoc]:
        request_ref = self._db.collection("quote_requests").document(qrid)
        quote_ref = self._quotes(qrid).document(qid)

        @firestore.transactional
        def run(tx: firestore.Transaction) -> tuple[QuoteRequest, QuoteDoc]:
            request, quote = change(
                QuoteRequest.model_validate(request_ref.get(transaction=tx).to_dict() | {"id": qrid}),
                QuoteDoc.model_validate(quote_ref.get(transaction=tx).to_dict() | {"id": qid}),
            )
            tx.set(request_ref, request.model_dump(exclude={"id"}))
            tx.set(quote_ref, quote.model_dump(exclude={"id"}))
            return request, quote

        return run(self._db.transaction())

    def first_delivery(self, update_id: int) -> bool:
        """Records a Telegram update; False if it was recorded before (Telegram retries a delivery it timed out)."""
        try:
            self._db.collection("tg_updates").document(str(update_id)).create(
                {"received_at": firestore.SERVER_TIMESTAMP}
            )
        except Conflict:
            return False
        return True
