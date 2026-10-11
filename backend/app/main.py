"""ustaad-api entry point. Routers for chat, media, jobs, inventory, quotes, imports and the
WhatsApp webhook are added in their own modules (spec §7)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ustaad-api", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Firebase Hosting forwards the full path, so every route also lives under /api (rest.md).
@app.get("/healthz")
@app.get("/api/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "flash_model": os.getenv("FLASH_MODEL", "unset"),
        "live_model": os.getenv("LIVE_MODEL", "unset"),
        "demo_safe": os.getenv("DEMO_SAFE", "0") == "1",
    }
