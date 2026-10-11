"""Create the empty Agent Engine instance that holds Memory Bank (spec §1, §6).

The agent itself runs on Cloud Run; this instance only stores memories. Print its resource name and
set AGENT_ENGINE_ID on Cloud Run to the trailing ID.

Usage: GOOGLE_CLOUD_PROJECT=... MEMORY_LOCATION=us-central1 uv run python infra/agent_engine.py
Memory Bank region availability: check the Memory Bank set-up docs before changing MEMORY_LOCATION.
"""

import os

import vertexai

client = vertexai.Client(
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.getenv("MEMORY_LOCATION", "us-central1"),
)
engine = client.agent_engines.create()
print(engine.api_resource.name)
