"""Step-by-step debug helper: dump the iOS XML AFTER EVERY tap.

Walks Lose It! through the picker flow and writes a numbered XML to reports/debug/
between each tap, so we can see exactly which step changes the screen state and
where the picker dies. Doesn't burn a Snap It free use (we never confirm a photo).

Run:
    python scripts/dump_picker_steps.py --config config/loseit_ramyarevati.yaml
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


def _dump(driver, out_dir: Path, step_idx: int, tag: str) -> None:
    safe_tag = "".join(c if c.isalnum() else "_" for c in tag)[:60] or "state"
    fname_xml = out_dir / f"step{step_idx:02d}_{safe_tag}.xml"
    fname_png = out_dir / f"step{step_idx:02d}_{safe_tag}.png"
    try:
        xml = driver.page_source
        fname_xml.write_text(xml, encoding="utf-8")
        print(f"  -> wrote {fname_xml.name} ({len(xml):,} chars)")
    except Exception as exc:
        print(f"  -> page_source failed: {exc!r}")
    try:
        driver.get_screenshot_as_file(str(fname_png))
        print(f"  -> wrote {fname_png.name}")
    except Exception as exc:
        print(f"  -> screenshot failed: {exc!r}")


def _tap(driver, locator, timeout, label):
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
    except Exception as exc:
        print(f"[fail] {label}: tap raised {exc!r}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    config = load_config(args.config)
    bundle = (config.get("app", {}) or {}).get("bundle_id", "com.fitnow.loseit")
    out_dir = ROOT / "reports" / "debug" / "step_trace"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"writing dumps to: {out_dir}")

    driver = create_ios_driver(config)
    try:
        try:
            driver.terminate_app(bundle)
        except Exception:
            pass
        driver.activate_app(bundle)
        time.sleep(2.5)
        _dump(driver, out_dir, 0, "after_app_launch")

        steps = [
            ("scan_entry",       loc.SCAN_ENTRY,                   25.0, "SCAN_ENTRY (Breakfast … menu)"),
            ("snap_it",          loc.SCAN_SECONDARY_TAP,           20.0, "SCAN_SECONDARY_TAP (Snap It)"),
            ("photo_library",    loc.PHOTO_LIBRARY_BUTTON,         15.0, "PHOTO_LIBRARY_BUTTON (green photo icon)"),
            ("collections_tab",  loc.PHOTO_PICKER_COLLECTIONS_TAB, 10.0, "PHOTO_PICKER_COLLECTIONS_TAB"),
            ("album_row",        loc.PHOTO_ALBUM_ROW,              20.0, "PHOTO_ALBUM_ROW (NutriSnapTests)"),
        ]

        for i, (tag, locator, timeout, label) in enumerate(steps, start=1):
            print(f"\n--- step {i}: {label} ---")
            ok = _tap(driver, locator, timeout, label)
            time.sleep(2.5)
            _dump(driver, out_dir, i, f"after_{tag}_{'ok' if ok else 'fail'}")
            if not ok:
                print(f"  -> stopping at step {i} since the tap failed")
                break

        print(f"\nDone. Inspect XML/PNG in {out_dir}")
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
