"""Placeholder vendors (made-up names and chat IDs), a quote request built from them, and in-memory stand-ins for
QuoteStore and TelegramBot."""

from collections.abc import Callable
from datetime import UTC, datetime

from models.quotes import QuoteDoc, QuoteRequest, Vendor
from models.telegram import Button
from tools import quotes

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
VENDORS = [
    Vendor(id="v_a", name="Vendor A", tg_chat_id=1001),
    Vendor(id="v_b", name="Vendor B", tg_chat_id=1002),
    Vendor(id="v_c", name="Vendor C", tg_chat_id=1003),
]


def sent_request(qrid="qr_1", now=NOW) -> tuple[QuoteRequest, list[QuoteDoc]]:
    """A request for an outdoor PCB, its message delivered to every vendor as message 500 + i."""
    request, docs = quotes.new_request(qrid, "j_1", "w_hi_demo", "outdoor PCB", "", 1, VENDORS, now)
    return request, [quotes.sent(q, 500 + i, now) for i, q in enumerate(docs)]


class FakeQuoteStore:
    def __init__(self, vendors=VENDORS) -> None:
        self.vendor_list = list(vendors)
        self.requests: dict[str, QuoteRequest] = {}
        self.quotes: dict[str, dict[str, QuoteDoc]] = {}
        self.seen_updates: set[int] = set()

    def vendors(self, worker_id: str) -> list[Vendor]:
        return self.vendor_list

    def create(self, request: QuoteRequest, docs: list[QuoteDoc]) -> None:
        self.requests[request.id] = request
        self.quotes[request.id] = {q.id: q for q in docs}

    def get(self, qrid: str) -> tuple[QuoteRequest, list[QuoteDoc]] | None:
        if qrid not in self.requests:
            return None
        return self.requests[qrid], list(self.quotes[qrid].values())

    def for_job(self, worker_id: str, job_id: str) -> list[tuple[QuoteRequest, list[QuoteDoc]]]:
        return [
            (request, list(self.quotes[request.id].values()))
            for request in self.requests.values()
            if request.worker_id == worker_id and request.job_id == job_id
        ]

    def find(self, qid: str, now: datetime) -> tuple[QuoteRequest, QuoteDoc] | None:
        return next(
            (
                (self.requests[qrid], docs[qid])
                for qrid, docs in self.quotes.items()
                if qid in docs and now < self.requests[qrid].expires_at
            ),
            None,
        )

    def update_quote(self, qrid: str, qid: str, change: Callable[[QuoteDoc], QuoteDoc]) -> QuoteDoc:
        self.quotes[qrid][qid] = change(self.quotes[qrid][qid])
        return self.quotes[qrid][qid]

    def approve(
        self, qrid: str, qid: str, change: Callable[[QuoteRequest, QuoteDoc], tuple[QuoteRequest, QuoteDoc]]
    ) -> tuple[QuoteRequest, QuoteDoc]:
        request, quote = change(self.requests[qrid], self.quotes[qrid][qid])
        self.requests[qrid], self.quotes[qrid][qid] = request, quote
        return request, quote

    def open_for_chat(self, chat_id: int, now: datetime) -> list[tuple[QuoteRequest, QuoteDoc]]:
        return [
            (self.requests[qrid], q)
            for qrid, docs in self.quotes.items()
            if self.requests[qrid].status == "open" and now < self.requests[qrid].expires_at
            for q in docs.values()
            if q.tg_chat_id == chat_id
        ]

    def first_delivery(self, update_id: int) -> bool:
        if update_id in self.seen_updates:
            return False
        self.seen_updates.add(update_id)
        return True


class FakeBot:
    def __init__(self, voice: bytes = b"OggS-fake") -> None:
        self.sent: list[tuple[int, str, list[Button]]] = []
        self.answered: list[str] = []
        self.voice = voice

    async def send_message(self, chat_id: int, text: str, buttons: list[Button] = ()) -> int:
        self.sent.append((chat_id, text, list(buttons)))
        return 900 + len(self.sent)

    async def answer_callback(self, callback_id: str) -> None:
        self.answered.append(callback_id)

    async def download_file(self, file_id: str) -> bytes:
        return self.voice
