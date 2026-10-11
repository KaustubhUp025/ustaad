"""T05 Live smoke test (owner A). UNTESTED starting point: adjust to the installed google-genai version.

For each language, opens a Live session on Agent Platform, sends one text turn, and checks that
(1) audio comes back, (2) an output transcription arrives, (3) its script looks right.
Record the result in docs/STATUS.md and docs/DECISIONS.md, then set LIVE_MODEL.

Usage: make smoke-live LIVE_MODEL=gemini-3.8-live
"""

import asyncio
import os
import sys

from google import genai
from google.genai import types

PROMPTS = {
    "hi-IN": ("AC par E6 error aa raha hai. Ek line mein batao pehle kya check karun.", "ऀ", "ॿ"),
    "te-IN": ("AC lo E6 error vastondi. Modata emi check cheyali? Okka line lo cheppandi.", "ఀ", "౿"),
    "ta-IN": ("AC-la E6 error varudhu. Mudhalla enna check pannanum? Oru line-la sollunga.", "஀", "௿"),
    "bn-IN": ("AC-te E6 error dekhachhe. Prothome ki check korbo? Ek line-e bolo.", "ঀ", "৿"),
}


async def one(client: genai.Client, model: str, lang: str, text: str, lo: str, hi: str) -> str:
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(language_code=lang),
    )
    audio_bytes, transcript = 0, ""
    async with client.aio.live.connect(model=model, config=config) as session:
        await session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=text)]), turn_complete=True
        )
        async for msg in session.receive():
            sc = msg.server_content
            if msg.data:
                audio_bytes += len(msg.data)
            if sc and sc.output_transcription and sc.output_transcription.text:
                transcript += sc.output_transcription.text
            if sc and sc.turn_complete:
                break
    native = any(lo <= ch <= hi for ch in transcript)
    status = "PASS" if audio_bytes and transcript and native else "CHECK"
    return f"{status} {lang}: audio={audio_bytes}B native_script={native} transcript={transcript[:80]!r}"


async def spoken_hindi(client: genai.Client, model: str, pcm_path: str) -> str:
    """Send a recorded clip (16 kHz mono PCM16, raw .pcm) as realtime audio and check the input transcription."""
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(language_code="hi-IN"),
    )
    data = open(pcm_path, "rb").read()
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
    for lang, (text, lo, hi) in PROMPTS.items():
        try:
            print(await one(client, model, lang, text, lo, hi))
        except Exception as e:  # report and continue to the next language
            print(f"FAIL {lang}: {type(e).__name__}: {e}")
    # Record ~5 s of Hindi, then: ffmpeg -i q.m4a -ac 1 -ar 16000 -f s16le seed/private/hindi_q.pcm
    pcm = os.getenv("SMOKE_PCM", "../seed/private/hindi_q.pcm")
    if os.path.exists(pcm):
        try:
            print(await spoken_hindi(client, model, pcm))
        except Exception as e:
            print(f"FAIL hi-IN speech: {type(e).__name__}: {e}")
    else:
        print(f"SKIP hi-IN speech: record a clip to {pcm} (see comment above)")


if __name__ == "__main__":
    asyncio.run(main())
