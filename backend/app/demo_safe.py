"""Demo-safe photo checks (BUILD-GUIDE T27): the live Flash call races a DEMO_FALLBACK_S timer; if the timer wins or
the call fails, the recorded real answer for the same question and the same image bytes is served. Only real model
answers are recorded, never errors and never hand-typed ones. This replaces only the vision call: a cached gate
verdict still goes through the same gate code, so safety behaves as with a live answer."""

import asyncio
import hashlib
import json
import os
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from agent.media_tools import ReadPhoto
from clients.firestore import DemoCacheStore

DEMO_FALLBACK_S = 6.0

def request_hash(question: str, schema: str, image_digest: str) -> str:
    """The question carries the target and the worker's language, so another language never gets this answer."""
    return hashlib.sha256(json.dumps([question, schema, image_digest]).encode()).hexdigest()


def demo_safe(
    read_photo: ReadPhoto, cache: DemoCacheStore, digest: Callable[[str], str], delay_s: float = 0.0
) -> ReadPhoto:
    """`digest` gives the stored image's content hash, so the same photo in another job's folder hits the record.
    `delay_s` slows the model on purpose, to test the fallback (DEMO_MODEL_DELAY_S)."""

    async def record(key: str, result: BaseModel) -> BaseModel:
        model = os.getenv("FLASH_MODEL", "unset")
        await asyncio.to_thread(cache.put, key, result.model_dump(mode="json"), model)
        return result

    async def read(question: str, uri: str, schema: type) -> Any:
        key = request_hash(question, schema.__name__, await asyncio.to_thread(digest, uri))

        async def live() -> BaseModel:
            await asyncio.sleep(delay_s)
            return await read_photo(question, uri, schema)

        task = asyncio.ensure_future(live())
        done, _ = await asyncio.wait({task}, timeout=DEMO_FALLBACK_S)
        if done and task.exception() is None:
            return await record(key, task.result())
        recorded = await asyncio.to_thread(cache.get, key)
        if recorded is not None:
            task.cancel()
            return schema.model_validate(recorded)
        return await record(key, await task)

    return read
