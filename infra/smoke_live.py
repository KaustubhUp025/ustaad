"""T05 Live smoke test (owner A).

For each language, opens a Live session on Agent Platform, sends one text turn, and checks that
(1) audio comes back, (2) an output transcription arrives, (3) its script looks right.
Then one tool-call round trip, and one spoken Hindi clip if a recording exists.
Record the result in docs/STATUS.md and docs/DECISIONS.md, then set LIVE_MODEL.

Usage: make smoke-live LIVE_MODEL=gemini-3.8-live [LIVE_LOCATION=global]
"""

import asyncio
import os
import sys
import time

from google import genai
from google.genai import types

PROMPTS = {
    "hi-IN": ("Hindi", "AC par E6 error aa raha hai. Ek line mein batao pehle kya check karun.", "ऀ", "ॿ"),
    "te-IN": ("Telugu", "AC lo E6 error vastondi. Modata emi check cheyali? Okka line lo cheppandi.", "ఀ", "౿"),
    "ta-IN": ("Tamil", "AC-la E6 error varudhu. Mudhalla enna check pannanum? Oru line-la sollunga.", "஀", "௿"),
    "bn-IN": ("Bengali", "AC-te E6 error dekhachhe. Prothome ki check korbo? Ek line-e bolo.", "ঀ", "৿"),
    "en-IN": ("English", "My AC is showing an E6 error. In one line, what should I check first?", "a", "z"),
}
TIMEOUT_S = 45  # a silent session would otherwise block in receive() for ever


async def one(client: genai.Client, model: str, lang: str, name: str, text: str, lo: str, hi: str) -> str:
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(language_code=lang),
        # language_code alone left the Tamil transcript in Latin letters
        system_instruction=f"Reply only in {name}, written in its own script.",
    )
    audio_bytes, transcript, first_ms = 0, "", None
    async with client.aio.live.connect(model=model, config=config) as session:
        sent = time.monotonic()
        await session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=text)]), turn_complete=True
        )
        async for msg in session.receive():
            sc = msg.server_content
            if msg.data:
                first_ms = first_ms or round((time.monotonic() - sent) * 1000)
                audio_bytes += len(msg.data)
            if sc and sc.output_transcription and sc.output_transcription.text:
                transcript += sc.output_transcription.text
            if sc and sc.turn_complete:
                break
    native = any(lo <= ch <= hi for ch in transcript)
    status = "PASS" if audio_bytes and transcript and native else "CHECK"
    return (f"{status} {lang}: first_audio={first_ms}ms audio={audio_bytes}B native_script={native} "
            f"transcript={transcript[:80]!r}")


async def tool_call(client: genai.Client, model: str) -> str:
    """One BLOCKING function call: the model must call it, then speak after the response."""
    fn = types.FunctionDeclaration(
        name="smoke_lookup",
        description="Look up a test value. Always call this before answering.",
        parameters_json_schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        behavior=types.Behavior.BLOCKING,
    )
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        tools=[types.Tool(function_declarations=[fn])],
        system_instruction="Call smoke_lookup for the code the user gives, then read its value aloud.",
    )
    called, audio_after = None, 0
    async with client.aio.live.connect(model=model, config=config) as session:
        await session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text="Look up code E6.")]), turn_complete=True
        )
        async for msg in session.receive():
            if msg.tool_call:
                fc = msg.tool_call.function_calls[0]
                called = dict(fc.args)
                await session.send_tool_response(function_responses=types.FunctionResponse(
                    id=fc.id, name=fc.name, response={"value": "smoke test value"}))
            if msg.data and called:
                audio_after += len(msg.data)
            if msg.server_content and msg.server_content.turn_complete:
                break
    status = "PASS" if called and audio_after else "CHECK"
    return f"{status} tool call: args={called} audio_after_response={audio_after}B"


async def spoken_hindi(client: genai.Client, model: str, pcm_path: str) -> str:
    """Send a recorded clip (16 kHz mono PCM16, raw .pcm) as realtime audio and check the input transcription."""
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(language_code="hi-IN"),
    )
    # A clip that ends mid-speech never closes the turn (audio_stream_end alone is not enough):
    # the model's voice detection needs to hear silence after the last word.
    data = open(pcm_path, "rb").read() + b"\0" * 48000  # 1.5 s of 16 kHz PCM16 silence
    heard, said = "", ""
    async with client.aio.live.connect(model=model, config=config) as session:
        for i in range(0, len(data), 1280):  # 40 ms chunks, like the PWA
            await session.send_realtime_input(audio=types.Blob(data=data[i:i + 1280], mime_type="audio/pcm;rate=16000"))
        await session.send_realtime_input(audio_stream_end=True)
        async for msg in session.receive():
            sc = msg.server_content
            if sc and sc.input_transcription and sc.input_transcription.text:
                heard += sc.input_transcription.text
            if sc and sc.output_transcription and sc.output_transcription.text:
                said += sc.output_transcription.text
            if sc and sc.turn_complete:
                break
    status = "PASS" if heard and said else "CHECK"
    return f"{status} hi-IN speech: heard={heard[:60]!r} replied={said[:60]!r}"


async def main() -> None:
    model = os.environ.get("LIVE_MODEL") or sys.exit("set LIVE_MODEL")
    # Same region the app uses (deploy.sh passes LIVE_LOCATION to Cloud Run)
    client = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                          location=os.getenv("LIVE_LOCATION", "us-central1"))
    for lang, prompt in PROMPTS.items():
        try:
            print(await asyncio.wait_for(one(client, model, lang, *prompt), TIMEOUT_S))
        except Exception as e:  # report and continue to the next language
            print(f"FAIL {lang}: {type(e).__name__}: {e}")
    try:
        print(await asyncio.wait_for(tool_call(client, model), TIMEOUT_S))
    except Exception as e:
        print(f"FAIL tool call: {type(e).__name__}: {e}")
    # Record ~5 s of Hindi, then: ffmpeg -i q.m4a -ac 1 -ar 16000 -f s16le seed/private/hindi_q.pcm
    pcm = os.getenv("SMOKE_PCM", "../seed/private/hindi_q.pcm")
    if os.path.exists(pcm):
        try:
            print(await asyncio.wait_for(spoken_hindi(client, model, pcm), TIMEOUT_S))
        except Exception as e:
            print(f"FAIL hi-IN speech: {type(e).__name__}: {e}")
    else:
        print(f"SKIP hi-IN speech: record a clip to {pcm} (see comment above)")


if __name__ == "__main__":
    asyncio.run(main())
