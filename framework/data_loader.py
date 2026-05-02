"""Load test cases from CSV or JSON (Deliverable 2B / 3D AI model shape — external data only)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .utils import normalize_app_key

# One executable row per (test_id, app_name) — 31 IDs × 3 apps = 93 rows in full suite.
# Input files may include template columns actual_output / result; the runner overwrites them in reports.
REQUIRED_COLUMNS = (
    "test_id",
    "app_name",
    "section",
    "subsection",
    "dimension_type",
    "sub_dimension",
    "item_description",
    "image_path",
    "expected_output",
)


def load_testcases(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Test data file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path)
    if suffix == ".json":
        return _load_json(path)
    raise ValueError(f"Unsupported test data format: {suffix} (use .csv or .json)")


def _load_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row.")
        headers = [h.strip() for h in reader.fieldnames]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
        for raw in reader:
            row = {k.strip(): (v or "").strip() if v is not None else "" for k, v in raw.items()}
            rows.append(row)
    return rows


def _load_json(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        payload: Any = json.load(f)
    if isinstance(payload, dict) and "testcases" in payload:
        payload = payload["testcases"]
    if not isinstance(payload, list):
        raise ValueError("JSON must be a list of testcase objects or {\"testcases\": [...]}.")
    out: list[dict[str, str]] = []
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"JSON testcase at index {i} is not an object.")
        row = {str(k): "" if item[k] is None else str(item[k]).strip() for k in item}
        missing = [c for c in REQUIRED_COLUMNS if c not in row]
        if missing:
            raise ValueError(f"JSON testcase {row.get('test_id', i)} missing: {missing}")
        out.append(row)
    return out


def filter_by_app(rows: list[dict[str, str]], app_key: str) -> list[dict[str, str]]:
    target = normalize_app_key(app_key)
    return [r for r in rows if normalize_app_key(r.get("app_name", "")) == target]


def filter_by_test_ids(
    rows: list[dict[str, str]], test_ids: list[str] | None
) -> list[dict[str, str]]:
    """Keep only rows whose `test_id` is in the requested set (case-insensitive).

    Pass ``None`` or empty to keep all rows. Useful for smoke runs or paywall-budgeted
    runs against apps with limited free uses (e.g. Lose It! Snap It).
    """
    if not test_ids:
        return rows
    wanted = {tid.strip().lower() for tid in test_ids if tid and tid.strip()}
    if not wanted:
        return rows
    return [r for r in rows if str(r.get("test_id", "")).strip().lower() in wanted]
