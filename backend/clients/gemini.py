"""Flash calls on Vertex (GOOGLE_GENAI_USE_VERTEXAI); the model ID comes from FLASH_MODEL."""

import mimetypes
import os

from google import genai
from google.genai import types
from pydantic import BaseModel


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
