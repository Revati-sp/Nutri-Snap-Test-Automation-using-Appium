"""One-off debug helper.

Walks Lose It! toward the iOS PHPicker album grid, **always** dumps page_source even if a step
fails partway, so we can build correct locators without burning a Snap It free use.

Run:
    python scripts/dump_picker_source.py --config config/loseit_ramyarevati.yaml

Output:
    reports/picker_grid_source.xml   — the raw XML at the deepest screen reached
    stdout                           — first 8 KB of XML for quick eyeballing
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.loseit import locators as loc
from framework.base_driver import create_ios_driver, safe_wait_until_visible
from framework.config_loader import load_config


def _tap_if_present(driver, locator, timeout, label):
    if not locator:
        print(f"[skip] {label}: locator not defined")
        return False
    el = safe_wait_until_visible(driver, locator, timeout=timeout)
    if not el:
        print(f"[skip] {label}: not visible after {timeout}s")
        return False
    try:
        el.click()
        print(f"[ok]   {label}: tapped")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[fail] {label}: tap raised {exc!r}")
        return False


def _safe_dump(driver, output_path: Path, tag: str) -> None:
    """Dump current page_source. Never raises — best-effort diagnostic."""
    try:
        xml = driver.page_source
    except Exception as exc:  # noqa: BLE001
        print(f"[dump:{tag}] page_source failed: {exc!r}")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml, encoding="utf-8")
    print(f"[dump:{tag}] wrote {len(xml):,} chars to {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "picker_grid_source.xml",
        help="Where to write the dumped XML.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    bundle = (config.get("app", {}) or {}).get("bundle_id", "com.fitnow.loseit")

    driver = create_ios_driver(config)
    try:
        try:
            driver.terminate_app(bundle)
        except Exception:
            pass
        driver.activate_app(bundle)
        time.sleep(2.0)

        steps = [
            ("scan_entry",       loc.SCAN_ENTRY,                   25.0, "SCAN_ENTRY (Breakfast … menu)"),
            ("snap_it",          loc.SCAN_SECONDARY_TAP,           10.0, "SCAN_SECONDARY_TAP (Snap It)"),
            ("photo_library",    loc.PHOTO_LIBRARY_BUTTON,         15.0, "PHOTO_LIBRARY_BUTTON (green photo icon)"),
            ("collections_tab",  loc.PHOTO_PICKER_COLLECTIONS_TAB, 10.0, "PHOTO_PICKER_COLLECTIONS_TAB"),
            ("album_row",        loc.PHOTO_ALBUM_ROW,              20.0, "PHOTO_ALBUM_ROW (NutriSnapTests)"),
        ]

        last_ok_tag = "before_anything"
        for tag, locator, timeout, label in steps:
            ok = _tap_if_present(driver, locator, timeout, label)
            time.sleep(2.0)  # let UI animations settle
            if ok:
                last_ok_tag = tag
            else:
                _safe_dump(driver, args.output, f"failed_at_{tag}")
                print(
                    f"\n[stop] step {tag!r} did not complete. Dumped current XML to {args.output} "
                    f"so you can see exactly what was on screen.\n"
                )
                return 0

        time.sleep(3.0)
        _safe_dump(driver, args.output, "after_album_open")
        try:
            xml = args.output.read_text(encoding="utf-8")
            print("=" * 80)
            print(xml[:8000])
            if len(xml) > 8000:
                print(f"... ({len(xml) - 8000:,} more chars in {args.output})")
        except Exception:
            pass
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
