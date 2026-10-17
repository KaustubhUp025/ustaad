from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from jobs.ingest.job import (
    IMPORT_FAILED,
    PREFLIGHT_FAILED,
    ImportJobDependencies,
    preflight,
    run_ingest_job,
)
from models.imports import CardDraft, DraftStep


class FakeImports:
    def __init__(self, status="queued", errors=None):
        self.status = status
        self.errors = errors or []
        self.updates = []

    def load(self, import_id):
        return {"status": self.status, "errors": self.errors}

    def update(self, import_id, **fields):
        self.updates.append(fields)
        self.status = fields.get("status", self.status)


class FakeStorage:
    def __init__(self):
        self.uploads = []

    def load_archive(self, import_id):
        return b"synthetic zip bytes"

    async def upload_derived(self, source: Path, destination_uri: str):
        self.uploads.append(destination_uri)
        return destination_uri


class FakeCards:
    def __init__(self):
        self.saved = []

    def nearest(self, brand, vector, limit):
        return []

    def save(self, card, vector):
        self.saved.append(card)


class FakeThreads:
    async def group_threads(self, messages):
        return {"groups": [[message.id for message in messages]]}


def draft(message_id):
    return CardDraft(
        resolved=True,
        brand="Voltas",
        model=None,
        appliance_type="split_ac",
        error_code="E6",
        symptom="Synthetic symptom",
        root_cause=None,
        steps=[DraftStep(text="Synthetic fix", summary_en="Inspect connector", hazard="none")],
        parts=[],
        fix_message_id=message_id,
        message_ids=[message_id],
        confidence=0.9,
        language="en",
    )


async def test_complete_offline_job_persists_lifecycle_counts_and_generated_audio_uri(tmp_path):
    imports = FakeImports()
    storage = FakeStorage()
    cards = FakeCards()
    chat = b"16/10/26, 9:00 am - Asha: voice.opus (file attached)"

    def read_archive(data):
        return SimpleNamespace(chat_bytes=chat, attachment_basenames=("voice.opus",))

    def materialize(data, names, directory):
        voice = directory / "voice.opus"
        voice.write_bytes(b"synthetic audio")
        return [voice]

    async def convert(source, destination):
        destination.write_bytes(b"synthetic flac")

    async def transcribe(source):
        return "Synthetic transcript"

    async def describe(source):
        return "Synthetic photo"

    async def ask(prompt, schema):
        message_id = prompt.split("[", 1)[1].split("]", 1)[0]
        return draft(message_id)

    deps = ImportJobDependencies(
        imports=imports,
        storage=storage,
        cards=cards,
        read_archive=read_archive,
        materialize=materialize,
        converter=convert,
        transcriber=transcribe,
        describer=describe,
        thread_client=FakeThreads(),
        ask=ask,
        embed=lambda texts, task: [[0.1, 0.2] for _ in texts],
        now=lambda: datetime(2026, 10, 17, tzinfo=UTC),
        workspace=tmp_path,
    )

    result = await run_ingest_job("i_complete", "ustaad101-media", deps)

    assert result is True
    assert [update["status"] for update in imports.updates] == [
        "parsing",
        "transcribing",
        "extracting",
        "done",
    ]
    assert imports.updates[-1] == {
        "status": "done",
        "audio_total": 1,
        "audio_done": 1,
        "threads": 1,
        "cards_created": 1,
        "cards_needing_review": 0,
        "errors": [],
        "finished_at": datetime(2026, 10, 17, tzinfo=UTC),
    }
    assert storage.uploads == ["gs://ustaad101-media/imports/i_complete/derived/m1.flac"]
    assert cards.saved[0].source.audio_uri == storage.uploads[0]


async def test_done_import_is_idempotent(tmp_path):
    imports = FakeImports(status="done")
    deps = ImportJobDependencies(imports=imports, workspace=tmp_path)

    assert await run_ingest_job("i_done", "ustaad101-media", deps) is True
    assert imports.updates == []


async def test_job_failure_persists_and_logs_only_fixed_safe_values(tmp_path, caplog):
    private = "private-export.zip token=SYNTHETIC_TOKEN gs://private/archive 9000000000"
    imports = FakeImports(errors=[private])

    class FailingStorage(FakeStorage):
        def load_archive(self, import_id):
            raise RuntimeError(private)

    deps = ImportJobDependencies(
        imports=imports,
        storage=FailingStorage(),
        workspace=tmp_path,
    )

    assert await run_ingest_job("i_failure", "ustaad101-media", deps) is False
    assert imports.updates == [
        {
            "status": "failed",
            "errors": [IMPORT_FAILED],
            "finished_at": imports.updates[0]["finished_at"],
        }
    ]
    exposed = str(imports.updates) + caplog.text
    for sensitive in (private, "private-export.zip", "SYNTHETIC_TOKEN", "gs://", "9000000000", "RuntimeError"):
        assert sensitive not in exposed


def test_preflight_allows_only_default_database_and_configured_bucket():
    assert preflight({"FIRESTORE_DB": "(default)", "MEDIA_BUCKET": "ustaad101-media", "IMPORT_ID": "i_1"})
    for env in (
        {"FIRESTORE_DB": "demo", "MEDIA_BUCKET": "ustaad101-media", "IMPORT_ID": "i_1"},
        {"FIRESTORE_DB": "(default)", "MEDIA_BUCKET": "wrong", "IMPORT_ID": "i_1"},
        {"FIRESTORE_DB": "(default)", "MEDIA_BUCKET": "ustaad101-media"},
    ):
        result = preflight(env)
        assert result.error == PREFLIGHT_FAILED
