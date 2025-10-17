"""FastAPI application exposing the text coding engine."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import SETTINGS, refresh_preset_cache
from .router_code import router as code_router
from .router_presets import router as presets_router
from .router_webhook import router as webhook_router

app = FastAPI(title="TextCoder Engine API", version=SETTINGS.ENGINE_VERSION)

origins = [origin.strip() for origin in SETTINGS.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(code_router)
app.include_router(presets_router)
app.include_router(webhook_router)


@app.on_event("startup")
def warm_cache() -> None:
    """Load presets into memory when the service starts."""

    refresh_preset_cache()
