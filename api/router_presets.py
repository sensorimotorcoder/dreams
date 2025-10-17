"""Routers for preset discovery, validation, and lexicon extension."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

from fastapi import APIRouter, HTTPException
from jsonschema import ValidationError, validate

from .deps import SETTINGS, get_presets_cache, load_british_american_map
from .lexicon_extender import apply_extenders
from .models import ExtendPayload, ExtendResult

router = APIRouter(prefix="", tags=["presets"])


@router.get("/presets", response_model=Dict[str, List[str]])
def list_presets() -> Dict[str, List[str]]:
    presets = get_presets_cache()
    return {"presets": sorted(presets.keys())}


@router.post("/validate_preset", response_model=Dict[str, Any])
def validate_preset(payload: Dict[str, Any]) -> Dict[str, Any]:
    schema_path = Path(SETTINGS.SCHEMA_PATH)
    if not schema_path.exists():
        raise HTTPException(status_code=500, detail="Schema not found")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        validate(payload, schema)
    except ValidationError as exc:  # pragma: no cover - hard to trigger deterministically
        return {"ok": False, "error": str(exc), "path": list(exc.path)}
    return {"ok": True}


@router.post("/extend_lexicon", response_model=ExtendResult)
def extend_lexicon(payload: ExtendPayload) -> ExtendResult:
    base_lexicons: Dict[str, List[str]] = {}
    base_exceptions: Dict[str, List[str]] = {}
    if payload.base_preset:
        presets = get_presets_cache()
        if payload.base_preset not in presets:
            raise HTTPException(status_code=400, detail=f"Unknown preset {payload.base_preset}")
        base_lexicons = presets[payload.base_preset].get("lexicons", {}) or {}
        base_exceptions = presets[payload.base_preset].get("exceptions", {}) or {}

    merged: Dict[str, List[str]] = {key: list(value) for key, value in base_lexicons.items()}
    for key, values in (payload.keywords or {}).items():
        merged.setdefault(key, [])
        merged[key] = sorted({*merged[key], *values})

    merged_exceptions: Dict[str, List[str]] = {
        key: list(value) for key, value in base_exceptions.items()
    }
    for key, values in (payload.exceptions or {}).items():
        merged_exceptions.setdefault(key, [])
        merged_exceptions[key] = sorted({*merged_exceptions[key], *values})

    br_am = load_british_american_map()

    proposed: Dict[str, List[Dict[str, Any]]] = {}
    combined_entries = list(merged.items()) + list(merged_exceptions.items())
    for key, terms in combined_entries:
        if payload.categories and not any(key.startswith(cat) for cat in payload.categories):
            continue
        proposals = apply_extenders(terms, br_am)
        flat: List[Dict[str, Any]] = []
        seen = {term.lower() for term in terms}
        for base_term, items in proposals.items():
            for item in items:
                term_value = item["term"]
                if term_value.lower() in seen:
                    continue
                flat.append({"term": term_value, "source": item["source"], "base": base_term})
                seen.add(term_value.lower())
        if flat:
            proposed[key] = flat

    return ExtendResult(proposed=proposed, conflicts=[], notes=[])
