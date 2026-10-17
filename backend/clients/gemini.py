"""Flash calls on Vertex (GOOGLE_GENAI_USE_VERTEXAI); the model ID comes from FLASH_MODEL."""

import mimetypes
import os
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel

# The WhatsApp import's calls: Vertex answers Flash with transient 429s even at one call at a time, and a call can hang
# (Oct 17 dev imports lost attachments, the thread grouping and threads to both). HttpRetryOptions() turns on the SDK's
# retry (off by default): 5 attempts with 1-8 s backoff on 408, 429 and 5xx, and on httpx timeouts, so a call that hangs
# past `timeout` is retried too (asserted against google.genai._api_client.retry_args in test_gemini_retry.py).
IMPORT_CALLS = types.HttpOptions(timeout=120_000, retry_options=types.HttpRetryOptions())
# A worker waits on live search and close_job: their embedding fails fast instead of retrying.
INTERACTIVE_EMBED = types.HttpOptions(timeout=10_000)


async def read_photo[M: BaseModel](question: str, media_uri: str, schema: type[M]) -> M:
    """Asks Flash one question about a photo in Cloud Storage and parses the answer into `schema`."""
    mime = mimetypes.guess_type(media_uri)[0] or "image/jpeg"
    # Held in a name: a temporary Client is collected mid-call, which closes its HTTP client under the request.
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model=os.environ["FLASH_MODEL"],
        contents=[types.Part.from_uri(file_uri=media_uri, mime_type=mime), question],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    return schema.model_validate_json(response.text)


async def ask_json[M: BaseModel](prompt: str, schema: type[M], http_options: types.HttpOptions | None = None) -> M:
    """Asks Flash a text-only question and parses the answer into `schema`."""
    client = genai.Client(http_options=http_options)
    response = await client.aio.models.generate_content(
        model=os.environ["FLASH_MODEL"],
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    return schema.model_validate_json(response.text)


async def hear_json[M: BaseModel](question: str, flac: bytes, schema: type[M]) -> M:
    """Asks Flash one question about a FLAC recording and parses the answer into `schema`."""
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model=os.environ["FLASH_MODEL"],
        contents=[types.Part.from_bytes(data=flac, mime_type="audio/flac"), question],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    return schema.model_validate_json(response.text)


def embed(
    texts: list[str], task_type: str, http_options: types.HttpOptions = INTERACTIVE_EMBED
) -> list[list[float]]:
    """EMBED_DIM must match the Firestore vector index (infra/firestore.sh), or search silently finds nothing."""
    client = genai.Client(http_options=http_options)
    response = client.models.embed_content(
        model=os.environ["EMBED_MODEL"],
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=int(os.environ["EMBED_DIM"])),
    )
    return [e.values for e in response.embeddings]


async def transcribe_import_audio(source: Path) -> str:
    client = genai.Client(http_options=IMPORT_CALLS)
    response = await client.aio.models.generate_content(
        model=os.getenv("TRANSCRIBE_MODEL") or os.environ["FLASH_MODEL"],
        contents=[
            "Transcribe exactly. Keep Hinglish, error codes and part numbers verbatim.",
            types.Part.from_bytes(data=source.read_bytes(), mime_type="audio/flac"),
        ],
    )
    return response.text or ""


async def describe_import_photo(source: Path) -> str:
    client = genai.Client(http_options=IMPORT_CALLS)
    mime = mimetypes.guess_type(source.name)[0] or "image/jpeg"
    response = await client.aio.models.generate_content(
        model=os.environ["FLASH_MODEL"],
        contents=[
            "Describe only visible appliance, model, code, component and condition details.",
            types.Part.from_bytes(data=source.read_bytes(), mime_type=mime),
        ],
    )
    return response.text or ""
