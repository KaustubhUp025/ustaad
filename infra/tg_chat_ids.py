"""Lists the Telegram chats that pressed Start on the quotes bot (getUpdates); with --seed, saves them as the demo
worker's vendors in the dev Firestore. Run it before infra/tg_set_webhook.sh: once a webhook is set, Telegram keeps no
updates for getUpdates. Chat IDs go only to Firestore, never into git (firestore.md).

Usage (from the repo root):
  TG_BOT_TOKEN=$(gcloud secrets versions access latest --secret tg-bot-token) \
    uv run --directory backend --env-file .env python ../infra/tg_chat_ids.py [--seed]
"""

import argparse
import hashlib
import os

import httpx
from google.cloud import firestore

WORKER_ID = "w_hi_demo"


def started_chats(token: str) -> dict[int, str]:
    body = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20).json()
    if not body["ok"]:
        raise SystemExit(f"getUpdates failed: {body.get('description')}")
    chats = (u["message"]["chat"] for u in body["result"] if "message" in u)
    return {c["id"]: c.get("first_name") or c.get("title") or "Vendor" for c in chats}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help=f"save them as {WORKER_ID}'s vendors on dev")
    args = parser.parse_args()
    chats = started_chats(os.environ["TG_BOT_TOKEN"])
    for chat_id, name in chats.items():
        print(chat_id, name)
    if not args.seed:
        return
    vendors = (
        firestore.Client(database="(default)").collection("workers").document(WORKER_ID).collection("vendors")
    )
    for chat_id, name in chats.items():
        # A stable ID that does not show the chat ID, which REST responses carry as vendor_id.
        vid = "v_" + hashlib.sha256(str(chat_id).encode()).hexdigest()[:10]
        vendors.document(vid).set(
            {
                "name": name,
                "tg_chat_id": chat_id,
                "place_id": None,
                "pincode": None,
                "categories": [],
                "reliability": None,
            }
        )
        print("saved", vid, name)


if __name__ == "__main__":
    main()
