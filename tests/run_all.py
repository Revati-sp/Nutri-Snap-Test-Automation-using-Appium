"""Batch runner: filter external test cases by app and execute with logging + stats."""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from appium.webdriver.webdriver import WebDriver

from apps.foodzilla.tests import run_single_test as run_foodzilla
from apps.loseit.tests import run_single_test as run_loseit
from apps.snapcalorie.tests import run_single_test as run_snapcalorie
from framework.base_driver import create_ios_driver, save_screenshot
from framework.config_loader import load_config
from framework.data_loader import filter_by_app, load_testcases
from framework.logger import get_logger, setup_logging
from framework.result_logger import append_result_csv
from framework.stats import format_summary, summarize_results
from framework.utils import normalize_app_key, project_root
from framework.validator import validate_outputs

setup_logging()
logger = get_logger(__name__)

AppRunner = Callable[[WebDriver, dict[str, str], dict[str, Any]], Tuple[str, Optional[str]]]

RUNNERS: dict[str, AppRunner] = {
    "foodzilla": run_foodzilla,
    "snapcalorie": run_snapcalorie,
    "loseit": run_loseit,
}


def _screenshot_path(report_dir: Path, test_id: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in test_id)[:80]
    return report_dir / "screenshots" / f"{safe_id}_{ts}.png"


def _pick_runner(app_name: str):
    key = normalize_app_key(app_name)
    if key not in RUNNERS:
        raise KeyError(f"No runner registered for app '{app_name}' (normalized: '{key}').")
    return RUNNERS[key]


def run_batch(
    config_path: Path,
    app_filter: str,
    data_path: Path,
    report_csv: Path,
) -> int:
    config = load_config(config_path)
    all_rows = load_testcases(data_path)
    rows = filter_by_app(all_rows, app_filter)
    if not rows:
        logger.error("No test cases for app filter %r in %s", app_filter, data_path)
        return 2

    runner = _pick_runner(app_filter)
    report_dir = report_csv.parent
    result_rows: list[dict[str, object]] = []
    driver: Optional[WebDriver] = None

    try:
        driver = create_ios_driver(config)
    except Exception:
        logger.exception("Failed to start Appium session — check server, caps, and device.")
        return 1

    try:
        for tc in rows:
            tid = tc.get("test_id", "")
            app_name = tc.get("app_name", "")
            err_msg = ""
            outcome = "ERROR"
            actual_output = ""

            try:
                actual_output, run_err = runner(driver, tc, config)
                if run_err:
                    outcome = "ERROR"
                    err_msg = run_err
                else:
                    vr = validate_outputs(tc, actual_output)
                    if vr.passed:
                        outcome = "PASS"
                    else:
                        outcome = "FAIL"
                        err_msg = vr.message
            except Exception:
                outcome = "ERROR"
                err_msg = traceback.format_exc()

            if outcome in {"FAIL", "ERROR"}:
                try:
                    shot = _screenshot_path(report_dir, tid or "unknown")
                    save_screenshot(driver, shot)
                except Exception:
                    logger.warning("Screenshot capture failed", exc_info=True)

            row_out = {
                "test_id": tid,
                "app_name": app_name,
                "section": tc.get("section", ""),
                "subsection": tc.get("subsection", ""),
                "dimension_type": tc.get("dimension_type", ""),
                "sub_dimension": tc.get("sub_dimension", ""),
                "item_description": tc.get("item_description", ""),
                "image_path": tc.get("image_path", ""),
                "expected_output": tc.get("expected_output", ""),
                "actual_output": actual_output,
                "result": outcome,
                "error_message": err_msg.replace("\n", " ").strip()[:2000],
            }
            append_result_csv(report_csv, row_out)
            result_rows.append({**row_out, "timestamp": ""})

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                logger.warning("driver.quit() raised", exc_info=True)

    summary = summarize_results(result_rows)
    logger.info(format_summary(summary))
    print(format_summary(summary))
    return 0 if summary.failed == 0 and summary.errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Appium iOS tests filtered by app_name.")
    parser.add_argument("--config", required=True, type=Path, help="Path to teammate local YAML")
    parser.add_argument("--app", required=True, help="App name to filter (e.g. FoodZilla, Lose It!)")
    parser.add_argument(
        "--data",
        type=Path,
        default=project_root() / "data" / "testcases.csv",
        help="CSV or JSON test case file",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=project_root() / "reports" / "results.csv",
        help="Append-only results CSV path",
    )
    args = parser.parse_args()
    return run_batch(args.config, args.app, args.data, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
