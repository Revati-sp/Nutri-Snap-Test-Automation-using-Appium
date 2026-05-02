"""Clean reports/ to a known-good baseline.

Keeps only the legitimate test rows (final TC01 PASS + TC02 FAIL from this Apple ID's
first batch) and removes:
  - All the FAIL/ERROR rows from earlier debugging runs
  - Orphan FAIL screenshots whose CSV row no longer exists
  - reports/debug/ — diagnostic XML/PNG dumps captured during locator triage
  - All historical test_report_<timestamp>.html files (test_report_latest.html stays)

Run:
    python scripts/cleanup_reports.py             # apply
    python scripts/cleanup_reports.py --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.result_logger import RESULT_COLUMNS

REPORTS = ROOT / "reports"


def _filter_to_keepers(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only the final/most-recent successful row per (test_id, app_name) pair.

    A row is "real" if it has a non-empty actual_output (i.e. the framework actually read
    something off the result screen). Earlier debugging rows with empty actual_output and
    FAIL "no rule accepted output (... actual='')" are dropped.
    """
    valid = [r for r in rows if str(r.get("actual_output", "")).strip()]
    latest_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for r in valid:
        key = (str(r.get("test_id", "")), str(r.get("app_name", "")))
        prior = latest_by_key.get(key)
        if prior is None or str(r.get("timestamp", "")) > str(prior.get("timestamp", "")):
            latest_by_key[key] = r
    return sorted(
        latest_by_key.values(),
        key=lambda r: (str(r.get("app_name", "")), int(r.get("test_id", "0") or "0")),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    args = parser.parse_args()

    csv_path = REPORTS / "results.csv"
    debug_dir = REPORTS / "debug"
    screenshots_dir = REPORTS / "screenshots"

    if not csv_path.exists():
        print(f"[skip] {csv_path} not found")
        return 0

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print(f"[skip] {csv_path} is empty")
            return 0
        # The contaminated CSV had an old header (no screenshot_path) but newer rows have an
        # extra screenshot_path column. Pad the header to the widest row, then build dicts.
        raw_rows = list(reader)
        max_cols = max((len(r) for r in raw_rows), default=len(header))
        # New schema (RESULT_COLUMNS) has screenshot_path BEFORE timestamp, so if the row has
        # exactly len(header)+1 columns, the extra one slots in just before timestamp.
        if max_cols > len(header):
            old_ts_idx = header.index("timestamp") if "timestamp" in header else len(header)
            header = header[:old_ts_idx] + ["screenshot_path"] + header[old_ts_idx:]
        rows: list[dict[str, str]] = []
        for r in raw_rows:
            padded = list(r) + [""] * (len(header) - len(r))
            rows.append({k.strip(): (v or "").strip() for k, v in zip(header, padded)})

    print(f"current {csv_path.name}: {len(rows)} rows")
    keepers = _filter_to_keepers(rows)
    print(f"after filtering: {len(keepers)} legitimate rows")
    for r in keepers:
        print(
            f"  - test_id={r.get('test_id')}  result={r.get('result')}  "
            f"expected={r.get('expected_output')!r}  actual={r.get('actual_output')!r}"
        )

    keep_screenshots = {Path(r.get("screenshot_path", "")).name for r in keepers if r.get("screenshot_path")}
    orphan_screens: list[Path] = []
    if screenshots_dir.exists():
        for p in screenshots_dir.iterdir():
            if not p.is_file():
                continue
            if p.name in keep_screenshots:
                continue
            orphan_screens.append(p)

    historical_reports = [
        p for p in REPORTS.glob("test_report_*.html") if p.name != "test_report_latest.html"
    ]
    misc_xml = list(REPORTS.glob("picker_grid_source.xml"))

    print(f"\nwill remove:")
    print(f"  reports/debug/                       (exists: {debug_dir.exists()})")
    print(f"  {len(orphan_screens)} orphan screenshot(s)")
    print(f"  {len(historical_reports)} historical test_report_*.html")
    print(f"  {len(misc_xml)} stray picker_grid_source.xml")

    if args.dry_run:
        print("\n[dry-run] no changes applied. Re-run without --dry-run to apply.")
        return 0

    backup = csv_path.with_suffix(".csv.bak")
    shutil.copy2(csv_path, backup)
    print(f"\n[backup] {csv_path} -> {backup.name}")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(RESULT_COLUMNS))
        writer.writeheader()
        for r in keepers:
            writer.writerow({k: r.get(k, "") for k in RESULT_COLUMNS})
    print(f"[write] {csv_path.name}: {len(keepers)} rows + header")

    if debug_dir.exists():
        shutil.rmtree(debug_dir)
        print(f"[remove] reports/debug/")

    for p in orphan_screens:
        p.unlink()
    if orphan_screens:
        print(f"[remove] {len(orphan_screens)} orphan screenshot(s)")

    for p in historical_reports:
        p.unlink()
    if historical_reports:
        print(f"[remove] {len(historical_reports)} historical test_report_*.html")

    for p in misc_xml:
        p.unlink()
    if misc_xml:
        print(f"[remove] {len(misc_xml)} stray xml file(s)")

    print("\nDone. Open reports/test_report_latest.html to confirm the 2 clean rows show up,")
    print("and run the next batch — new rows will append to the cleaned results.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
