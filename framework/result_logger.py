"""Append structured test results to CSV under reports/."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

RESULT_COLUMNS = (
    "test_id",
    "app_name",
    "section",
    "subsection",
    "dimension_type",
    "sub_dimension",
    "item_description",
    "image_path",
    "expected_output",
    "actual_output",
    "result",
    "error_message",
    "screenshot_path",
    "timestamp",
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_result_csv(report_path: str | Path, row: Mapping[str, Any]) -> Path:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not report_path.exists() or report_path.stat().st_size == 0
    line = {k: row.get(k, "") for k in RESULT_COLUMNS}
    if not line.get("timestamp"):
        line["timestamp"] = _utc_timestamp()
    with report_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(RESULT_COLUMNS))
        if write_header:
            writer.writeheader()
        writer.writerow({k: str(line.get(k, "")) for k in RESULT_COLUMNS})
    return report_path
