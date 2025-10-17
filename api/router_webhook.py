"""GitHub webhook for refreshing cached presets."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request

from .deps import SETTINGS, refresh_preset_cache
from .router_code import clear_preset_engines

router = APIRouter(prefix="", tags=["webhook"])


def _verify_signature(body: bytes, signature: str) -> bool:
    if not signature:
        return False
    digest = hmac.new(SETTINGS.GITHUB_WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    expected = "sha256=" + digest.hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/gh/webhook")
async def github_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    refreshed = refresh_preset_cache()
    clear_preset_engines()
    return {"ok": True, "count": len(refreshed)}
