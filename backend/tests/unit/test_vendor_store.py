"""Vendors as quote requests read them (firestore.md, approved Oct 17): a shop named in onboarding has no Telegram
chat until it is linked, so no quote request goes to it; a linked vendor is read with its chat."""

from types import SimpleNamespace

from clients.firestore import QuoteStore


class FakeDb:
    """Just enough of the Firestore client for workers/{wid}/vendors."""

    def __init__(self, vendors: dict[str, dict]) -> None:
        self.vendors = vendors

    def collection(self, name):
        return self

    def document(self, name):
        return self

    def stream(self):
        return [SimpleNamespace(id=vid, to_dict=lambda d=data: d) for vid, data in self.vendors.items()]


def test_a_shop_without_a_telegram_chat_gets_no_quote_request():
    db = FakeDb({"v_linked": {"name": "Test Linked Shop", "tg_chat_id": 111}, "v_onb": {"name": "Test Named Shop"}})
    assert [(v.id, v.name, v.tg_chat_id) for v in QuoteStore(db).vendors("w_1")] == [
        ("v_linked", "Test Linked Shop", 111)
    ]
