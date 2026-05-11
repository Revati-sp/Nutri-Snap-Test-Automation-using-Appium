"""Regenerate reports/test_report_latest.html from the existing reports/results.csv.

Useful when:
  * The HTML report schema changes (adding new sections like cost / complexity) and you
    want the existing CSV to be re-rendered without re-running tests on the device.
  * `duration_seconds` was empty for legacy rows; pass `--default-duration` to fill in a
    sensible per-test estimate so the runtime stats aren't blank.

Run:
    python scripts/regenerate_report.py
    python scripts/regenerate_report.py --default-duration 49.5
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.complexity import measure_repository
from framework.report_generator import write_html_report
from framework.stats import compute_batch_statistics, summarize_results


def _parse_ts(val: str):
    if not (val or "").strip():
        return None
    try:
        return datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _batch_window_from_rows(rows: list[dict[str, str]]) -> tuple[str | None, str | None]:
    """Earliest and latest per-row `timestamp` from CSV, if parseable."""
    times = []
    for r in rows:
        dt = _parse_ts(r.get("timestamp", ""))
        if dt is not None:
            times.append(dt)
    if not times:
        return None, None
    times.sort()
    return times[0].isoformat(), times[-1].isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "reports" / "results.csv",
        help="Source results CSV (default: reports/results.csv)",
    )
    parser.add_argument(
        "--app",
        default="(all rows in CSV)",
        help="Label to display in the report header (does not filter rows)",
    )
    parser.add_argument(
        "--default-duration",
        type=float,
        default=None,
        help="If a row has empty duration_seconds, use this value (s). Useful for legacy rows.",
    )
    args = parser.parse_args()

    if not args.csv.is_file():
        print(f"[error] CSV not found: {args.csv}")
        return 1

    with args.csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k is not None}
            if args.default_duration is not None and not row.get("duration_seconds"):
                row["duration_seconds"] = str(args.default_duration)
            rows.append(row)

    if not rows:
        print(f"[skip] {args.csv} has no data rows")
        return 0

    summary = summarize_results(rows)
    statistics = compute_batch_statistics(rows)
    complexity = measure_repository(ROOT)

    out_dir = args.csv.parent
    now_iso = datetime.now(timezone.utc).isoformat()
    stem_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    timestamped = out_dir / f"test_report_{stem_ts}.html"
    latest = out_dir / "test_report_latest.html"

    batch_start, batch_end = _batch_window_from_rows(rows)
    started_iso = batch_start or "(no timestamp column / empty values in CSV)"
    finished_iso = batch_end or now_iso

    for out in (timestamped, latest):
        write_html_report(
            output_path=out,
            rows=rows,
            summary=summary,
            app_filter=args.app,
            config_path=Path("(regenerated from CSV)"),
            data_path=args.csv,
            started_iso=started_iso,
            finished_iso=finished_iso,
            statistics=statistics,
            complexity=complexity,
        )

    print(f"Wrote {timestamped}")
    print(f"Wrote {latest}")
    print(
        f"Summary: total={summary.total} pass={summary.passed} fail={summary.failed} "
        f"errors={summary.errors} pass_rate={summary.pass_rate:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
