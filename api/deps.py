"""Shared dependencies and configuration for the FastAPI service."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import threading

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for the API layer."""

    PRESET_DIR: str = "configs/presets"
    SCHEMA_PATH: str = "schema/ruleset.schema.json"
    ENGINE_VERSION: str = "0.3.0"
    GITHUB_WEBHOOK_SECRET: str = "CHANGE_ME"
    CORS_ALLOW_ORIGINS: str = "*"

    class Config:
        env_file = ".env"


SETTINGS = Settings()

# In-memory preset cache protected by a re-entrant lock to make reloads thread-safe.
_PRESETS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.RLock()


def load_presets() -> Dict[str, Dict[str, Any]]:
    """Load all preset JSON payloads from the configured directory."""

    base = Path(SETTINGS.PRESET_DIR)
    loaded: Dict[str, Dict[str, Any]] = {}
    if not base.exists():
        return loaded

    for preset_path in base.glob("*.json"):
        with preset_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        name = data.get("meta", {}).get("name", preset_path.stem)
        version = data.get("meta", {}).get("version", "0.0.0")
        loaded[f"{name}@{version}"] = data
    return loaded


def refresh_preset_cache() -> Dict[str, Dict[str, Any]]:
    """Refresh the cached presets and return the new mapping."""

    global _PRESETS
    with _LOCK:
        _PRESETS = load_presets()
        return dict(_PRESETS)


def get_presets_cache() -> Dict[str, Dict[str, Any]]:
    """Return the cached presets, loading them if necessary."""

    if not _PRESETS:
        refresh_preset_cache()
    return _PRESETS


def load_british_american_map(path: str = "configs/british_american.yml") -> Dict[str, str]:
    """Load the British↔American spelling substitution map if present."""

    spelling_map = Path(path)
    if not spelling_map.exists():
        return {}
    with spelling_map.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    # Ensure the mapping is string to string for downstream consumers.
    return {str(k): str(v) for k, v in data.items()}
