"""Small shared helpers (paths, strings, timing hooks)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def project_root() -> Path:
    """Return repository root (parent of `framework/`)."""
    return Path(__file__).resolve().parent.parent


def resolve_path(path: str | Path, base: Optional[Path] = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    root = base or project_root()
    return (root / p).resolve()


def env_truthy(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_app_key(name: str) -> str:
    """Normalize app display names for matching (e.g. 'Lose It!' -> 'loseit')."""
    cleaned = "".join(ch.lower() for ch in name if ch.isalnum() or ch.isspace())
    return cleaned.replace(" ", "")
