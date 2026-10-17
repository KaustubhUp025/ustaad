"""ffmpeg: a voice note (Telegram's Ogg/Opus) to 16 kHz mono FLAC, the audio Flash reads (DECISIONS, Oct 11)."""

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
