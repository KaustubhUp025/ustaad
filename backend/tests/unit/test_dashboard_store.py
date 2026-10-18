"""Offline Firestore-store coverage for the dashboard's scoped reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from google.api_core.exceptions import Conflict

from clients.firestore import PUBLIC_FAULT_CARD_FIELDS, CardStore, DashboardStore, ImportStore, JobStore

NOW = datetime(2026, 10, 18, 12, tzinfo=UTC)


@dataclass
class Snapshot:
    id: str
    data: dict

    @property
    def exists(self) -> bool:
        return True

    def to_dict(self) -> dict:
        return self.data


@dataclass
class Query:
    db: FakeFirestore
    name: str
    filters: list[tuple[str, str, object]] = field(default_factory=list)
    fields: tuple[str, ...] | None = None

    def where(self, *, filter):
        return Query(self.db, self.name, [*self.filters, (filter.field_path, filter.op_string, filter.value)], self.fields)

    def select(self, fields):
        return Query(self.db, self.name, self.filters, tuple(fields))

    def count(self):
        return CountQuery(self)

    def stream(self):
        self.db.queries.append(self)
        docs = self.db.docs.get(self.name, {})
        for doc_id, data in docs.items():
            if not all(_matches(data, condition) for condition in self.filters):
                continue
            selected = data if self.fields is None else {key: data[key] for key in self.fields if key in data}
            yield Snapshot(doc_id, selected)

    def document(self, doc_id):
        return DocumentRef(self.db, self.name, doc_id)


@dataclass
class CountResult:
    value: int


@dataclass
class CountQuery:
    query: Query

    def get(self):
        return [[CountResult(len(list(self.query.stream())))]]


def _matches(data: dict, condition: tuple[str, str, object]) -> bool:
    field_name, op, expected = condition
    value = data.get(field_name)
    return op == "==" and value == expected


@dataclass
class DocumentRef:
    db: FakeFirestore
    collection_name: str
    id: str

    def create(self, data: dict) -> None:
        collection = self.db.docs.setdefault(self.collection_name, {})
        if self.id in collection:
            raise Conflict("already exists")
        collection[self.id] = data


class FakeFirestore:
    def __init__(self, docs: dict[str, dict[str, dict]]) -> None:
        self.docs = docs
        self.queries: list[Query] = []

    def collection(self, name: str) -> Query:
        return Query(self, name)


def _import(worker_id: str, started_at: datetime) -> dict:
    return {
        "worker_id": worker_id,
        "group_name": "Synthetic group",
        "status": "done",
        "files_total": 2,
        "audio_total": 1,
        "audio_done": 1,
        "threads": 1,
        "cards_created": 1,
        "cards_needing_review": 0,
        "errors": [],
        "started_at": started_at,
        "finished_at": started_at,
    }


def _card(review_status: str, *, symptom: str = "Drain pump blocked") -> dict:
    return {
        "embedding": "server-only-vector",
        "created_at": NOW,
        "brand": "Voltas",
        "error_code": "E6",
        "symptom": symptom,
        "fix_steps": ["Synthetic step"],
        "hazard": "none",
        "source": {"type": "synthetic"},
        "confidence": 0.9,
        "review_status": review_status,
    }


def test_summary_scopes_jobs_and_imports_to_worker_and_applies_the_window_without_a_composite_query():
    db = FakeFirestore(
        {
            "fault_cards": {"fc_one": _card("needs_review"), "fc_two": _card("approved"), "fc_three": _card("needs_review")},
            "jobs": {
                "j_recent": {"worker_id": "w_own", "created_at": NOW - timedelta(days=2)},
                "j_old": {"worker_id": "w_own", "created_at": NOW - timedelta(days=8)},
                "j_other": {"worker_id": "w_other", "created_at": NOW - timedelta(days=1)},
            },
            "imports": {
                "i_own_one": _import("w_own", NOW - timedelta(hours=1)),
                "i_own_two": _import("w_own", NOW - timedelta(days=1)),
                "i_other": _import("w_other", NOW),
            },
        }
    )

    assert DashboardStore(db).summary("w_own", NOW).model_dump() == {
        "cards": 3,
        "cards_needing_review": 2,
        "jobs_7d": 1,
        "imports": 2,
    }
    job_query = next(query for query in db.queries if query.name == "jobs")
    assert job_query.filters == [("worker_id", "==", "w_own")]
    assert job_query.fields == ("created_at",)
    assert any(query.name == "fault_cards" and query.fields is None for query in db.queries)


def test_imports_are_worker_scoped_newest_first_and_limited_without_a_composite_query():
    docs = {f"i_{number:02d}": _import("w_own", NOW - timedelta(minutes=number)) for number in range(22)}
    docs["i_other"] = _import("w_other", NOW + timedelta(minutes=1))
    db = FakeFirestore({"imports": docs})

    records = ImportStore(db).list("w_own")

    assert [record.id for record in records] == [f"i_{number:02d}" for number in range(20)]
    query = db.queries[-1]
    assert query.filters == [("worker_id", "==", "w_own")]
    assert query.fields is not None and "worker_id" in query.fields


def test_card_list_selects_only_public_fields_and_never_exposes_embeddings():
    db = FakeFirestore({"fault_cards": {"fc_one": _card("approved")}})

    cards = CardStore(db).list()

    assert cards[0].id == "fc_one"
    assert "embedding" not in cards[0].model_dump()
    assert db.queries[-1].fields == PUBLIC_FAULT_CARD_FIELDS


def test_new_job_records_write_documented_worker_and_creation_fields_once():
    db = FakeFirestore({"jobs": {}})
    store = JobStore(db)

    store.create("j_new", "w_own", NOW)
    store.create("j_new", "w_other", NOW + timedelta(days=1))

    assert db.docs["jobs"]["j_new"] == {"worker_id": "w_own", "created_at": NOW}
