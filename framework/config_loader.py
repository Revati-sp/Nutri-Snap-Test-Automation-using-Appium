"""Load and normalize YAML configuration for local machine, device, and app."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a nested dict."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, Mapping):
        raise ValueError("Config root must be a mapping (YAML object).")
    return dict(_normalize_keys(data))


def _normalize_keys(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _normalize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_keys(x) for x in obj]
    return obj


def get_nested(config: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = config
    for k in keys:
        if not isinstance(cur, Mapping) or k not in cur:
            return default
        cur = cur[k]
    return cur
