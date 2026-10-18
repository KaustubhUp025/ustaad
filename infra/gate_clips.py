"""Records each safety gate's fixed on-screen text as audio, once, with TTS_MODEL on Agent Platform.

SAFETY.md Enforcement 6 mutes Ustaad while a gate is open, so the phone plays these clips of the gate screen's own
text (phone test, Oct 18: the browser's speech voice was silent). Output is raw 24 kHz 16-bit mono PCM, the format
web/src/audio/playback.worklet.ts plays. Run again after any change to repair.gate or repair.evidence; the web test
gateClips.test.ts fails until you do.

Usage: make gate-clips
"""

import io
import json
import os
import wave
from pathlib import Path

from google import genai
from google.genai import types

WEB = Path(__file__).resolve().parent.parent / "web"
LANGS = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN", "ta": "ta-IN", "bn": "bn-IN"}
GATES = ("G_MAINS_OFF", "G_CAP_DISCHARGE")
RATE = 24000


def pcm(mime_type: str, data: bytes) -> bytes:
    """The model answers with raw PCM or with WAV, depending on the endpoint; the player takes raw 24 kHz mono 16-bit."""
    if mime_type.startswith("audio/L16") and f"rate={RATE}" in mime_type:
        return data
    with wave.open(io.BytesIO(data)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 1, 2):
            raise SystemExit(f"got {w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()} bit")
        return w.readframes(w.getnframes())


def main() -> None:
    client = genai.Client()
    model = os.environ["TTS_MODEL"]
    texts: dict[str, dict[str, str]] = {}
    for lang, code in LANGS.items():
        repair = json.loads((WEB / "src/i18n" / f"{lang}.json").read_text())["repair"]
        texts[lang] = {}
        for gate in GATES:
            text = f"{repair['gate'][gate]} {repair['evidence'][gate]}"
            res = client.models.generate_content(
                model=model,
                # The text alone: the model reads any instruction sent with it aloud, and refuses a system instruction.
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(language_code=code),
                ),
            )
            blob = res.candidates[0].content.parts[0].inline_data
            audio = pcm(blob.mime_type, blob.data)
            out = WEB / "public/audio/gates" / lang / f"{gate}.pcm"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(audio)
            texts[lang][gate] = text
            print(f"{lang} {gate}: {len(audio) / (2 * RATE):.1f} s")
    (WEB / "src/audio/gateClips.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
