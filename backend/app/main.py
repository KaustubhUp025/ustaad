"""ustaad-api entry point. Routers for chat, media, jobs, inventory, quotes, imports and the
Telegram vendor webhook are added in their own modules (spec §7)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dashboard import router as dashboard_router
from app.demo_session import router as demo_session_router
from app.errors import HTTP_ERRORS, install_error_handlers
from app.fault_cards import router as fault_cards_router
from app.imports import router as imports_router
from app.inventory import router as inventory_router
from app.media import router as media_router
from app.quotes import router as quotes_router
from app.telegram import router as telegram_router
from app.ws_live import router as ws_live_router
from models.errors import ErrorResponse

ERROR_RESPONSES = {
    status: {"model": ErrorResponse}
    for status in HTTP_ERRORS
}

app = FastAPI(title="ustaad-api", version="0.1.0", responses=ERROR_RESPONSES)
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(demo_session_router)
app.include_router(dashboard_router)
app.include_router(fault_cards_router)
app.include_router(imports_router)
app.include_router(media_router)
app.include_router(inventory_router)
app.include_router(quotes_router)
app.include_router(telegram_router)
app.include_router(ws_live_router)


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
