"""Endpoints for running the rule engine against submitted rows."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict, Any

import yaml
from fastapi import APIRouter, HTTPException

from .deps import SETTINGS, get_presets_cache
from .models import CodePayload
from src.rules import RuleEngine


_BASE_CATEGORIES = {}
_BASE_EXCEPTIONS = {}
if Path("config/categories.yml").exists():
    with Path("config/categories.yml").open("r", encoding="utf-8") as fh:
        _BASE_CATEGORIES = yaml.safe_load(fh)
if Path("config/exceptions.yml").exists():
    with Path("config/exceptions.yml").open("r", encoding="utf-8") as fh:
        _BASE_EXCEPTIONS = yaml.safe_load(fh)

_DEFAULT_ENGINE = RuleEngine(_BASE_CATEGORIES, _BASE_EXCEPTIONS)
_PRESET_ENGINES: Dict[str, RuleEngine] = {}

router = APIRouter(prefix="", tags=["code"])


def _merge_dotted(target: Dict[str, Any], dotted_key: str, values: Any) -> None:
    parts = dotted_key.split(".")
    cursor = target
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    leaf = parts[-1]
    existing = cursor.get(leaf)
    if isinstance(existing, list) and isinstance(values, list):
        merged = list(dict.fromkeys(existing + values))
        cursor[leaf] = merged
    else:
        cursor[leaf] = values


def _engine_for_ruleset(name: str, ruleset: Dict[str, Any]) -> RuleEngine:
    if name in _PRESET_ENGINES:
        return _PRESET_ENGINES[name]

    cats = deepcopy(_BASE_CATEGORIES)
    excs = deepcopy(_BASE_EXCEPTIONS)

    for key, vals in (ruleset.get("lexicons") or {}).items():
        _merge_dotted(cats, key, list(vals))
    for key, vals in (ruleset.get("exceptions") or {}).items():
        _merge_dotted(excs, key, list(vals))

    engine = RuleEngine(cats, excs)
    _PRESET_ENGINES[name] = engine
    return engine


def clear_preset_engines() -> None:
    """Clear cached preset-specific engine instances."""

    _PRESET_ENGINES.clear()


@router.post("/code", response_model=Dict[str, Any])
def code_rows(payload: CodePayload) -> Dict[str, Any]:
    presets = get_presets_cache()
    ruleset = None
    preset_version = "ad-hoc"

    if payload.preset:
        if payload.preset not in presets:
            raise HTTPException(status_code=400, detail=f"Unknown preset {payload.preset}")
        ruleset = presets[payload.preset]
        preset_version = payload.preset.split("@")[-1]

    if ruleset is None:
        engine = _DEFAULT_ENGINE
    else:
        assert payload.preset is not None  # for type-checkers
        engine = _engine_for_ruleset(payload.preset, ruleset)

    results = []
    for row in payload.rows:
        analysis = engine.analyze_text(row.text)
        results.append(
            {
                "row": row.row,
                "code_version": SETTINGS.ENGINE_VERSION,
                "preset_version": preset_version,
                "coded": analysis,
            }
        )

    return {"results": results}
