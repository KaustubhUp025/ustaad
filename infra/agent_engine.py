"""Create the empty Agent Engine instance that holds Memory Bank (spec §1, §6), or update its Memory Bank topics.

The agent itself runs on Cloud Run; this instance only stores memories. With AGENT_ENGINE_ID unset it creates the
instance and prints its resource name (set AGENT_ENGINE_ID on Cloud Run to the trailing ID); with it set it updates
that instance's topics.

Usage: GOOGLE_CLOUD_PROJECT=... MEMORY_LOCATION=us-central1 [AGENT_ENGINE_ID=...] uv run python infra/agent_engine.py
Memory Bank region availability: check the Memory Bank set-up docs before changing MEMORY_LOCATION.
"""

import os

import vertexai

# What Memory Bank extracts (S3 coaching). With the default topics it kept "weak at inverter PCB checks" but dropped
# "always talk to me in Hindi" from the same turn (Oct 18), so the two facts Ustaad needs are named topics.
TOPICS = [
    {"managed_memory_topic": {"managed_topic_enum": "USER_PERSONAL_INFO"}},
    {"managed_memory_topic": {"managed_topic_enum": "USER_PREFERENCES"}},
    {
        "custom_memory_topic": {
            "label": "preferred_language",
            "description": "The language the technician wants Ustaad to speak with him: Hindi, Telugu, Tamil, Bengali "
            "or English, including requests such as 'always talk to me in Hindi'.",
        }
    },
    {
        "custom_memory_topic": {
            "label": "skill_gaps",
            "description": "Repairs, parts or diagnosis skills the technician says he is weak at, struggles with or "
            "wants to learn, such as inverter AC PCB checks.",
        }
    },
]
CONFIG = {"context_spec": {"memory_bank_config": {"customization_configs": [{"memory_topics": TOPICS}]}}}

project = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.getenv("MEMORY_LOCATION", "us-central1")
client = vertexai.Client(project=project, location=location)
engine_id = os.getenv("AGENT_ENGINE_ID")
if engine_id:
    name = f"projects/{project}/locations/{location}/reasoningEngines/{engine_id}"
    engine = client.agent_engines.update(name=name, config=CONFIG)
else:
    engine = client.agent_engines.create(config=CONFIG)
print(engine.api_resource.name)
print(engine.api_resource.context_spec)
