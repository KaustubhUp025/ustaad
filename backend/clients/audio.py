"""ffmpeg: a voice note (a Telegram reply or an imported WhatsApp note) to 16 kHz mono FLAC, the audio Flash reads
(DECISIONS, Oct 11). The one converter: the Telegram webhook and the import job (T13) both use it."""

import asyncio


async def to_flac(audio: bytes) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *(
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "flac",
            "pipe:1",
        ),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    flac, _ = await process.communicate(audio)
    if process.returncode != 0:
        raise RuntimeError("audio conversion failed")
    return flac
