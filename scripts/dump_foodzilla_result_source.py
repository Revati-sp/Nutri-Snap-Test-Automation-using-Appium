"""Capture FoodZilla accessibility XML on the meal-analysis screen (Inspector-style snapshot).

Use when locators / fallback scans cannot read ``actual_output``: open the dumped XML in a text
editor or Appium Inspector source tab and mine predicates for ``RESULT_PANEL`` /
``RESULT_PANEL_CANDIDATES`` / ``RESULT_SCAN_EXCLUDE_SUBSTRINGS``.

Run (automated flow — gallery pick then wait):
    .venv/bin/python3 scripts/dump_foodzilla_result_source.py --config config/kavya_foodzilla.yaml

Manual — you navigate to the result screen, script only waits then dumps:
    .venv/bin/python3 scripts/dump_foodzilla_result_source.py --config config/kavya_foodzilla.yaml --mode manual --manual-wait 45

Outputs under ``reports/debug/``:
    foodzilla_result_<tag>_<utc>.xml   — full page_source
    foodzilla_result_<tag>_<utc>.txt  — deduped label="" / name="" strings (quick scan)
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.foodzilla.page import FoodzillaPage
from framework.base_driver import create_ios_driver
from framework.config_loader import load_config
from framework.utils import resolve_path


def _extract_attributed_strings(xml: str, attr: str) -> list[str]:
    pat = re.compile(rf'{re.escape(attr)}="([^"]{{2,400}})"')
    seen: set[str] = set()
    out: list[str] = []
    for m in pat.finditer(xml):
        s = m.group(1).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _summarize_xml(xml: str) -> str:
    labels = _extract_attributed_strings(xml, "label")
    names = _extract_attributed_strings(xml, "name")
    merged: list[str] = []
    seen: set[str] = set()
    for s in labels + names:
        sl = s.strip()
        if sl and sl.lower() not in seen:
            seen.add(sl.lower())
            merged.append(sl)
    lines = ["# deduped label/name strings (case-insensitive)", ""]
    lines.extend(merged[:250])
    if len(merged) > 250:
        lines.append("")
        lines.append(f"# ... {len(merged) - 250} more omitted")
    return "\n".join(lines) + "\n"


def _dump(driver, out_dir: Path, tag: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(c if c.isalnum() else "_" for c in tag)[:48] or "dump"
    xml_path = out_dir / f"foodzilla_result_{safe}_{ts}.xml"
    txt_path = out_dir / f"foodzilla_result_{safe}_{ts}.txt"
    xml = driver.page_source
    xml_path.write_text(xml, encoding="utf-8")
    txt_path.write_text(_summarize_xml(xml), encoding="utf-8")
    print(f"[dump] XML -> {xml_path} ({len(xml):,} chars)")
    print(f"[dump] label/name summary -> {txt_path}")
    return xml_path, txt_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump FoodZilla page_source after meal analysis.")
    parser.add_argument("--config", required=True, type=Path, help="YAML e.g. config/kavya_foodzilla.yaml")
    parser.add_argument(
        "--mode",
        choices=("automated", "manual"),
        default="automated",
        help="automated: scan→gallery→image; manual: foreground app then wait for you.",
    )
    parser.add_argument("--image", default="data/images/TC01.jpg", help="Relative to project root (automated).")
    parser.add_argument(
        "--analyze-wait",
        type=float,
        default=70.0,
        help="Seconds to wait after picking photo before dump (automated).",
    )
    parser.add_argument(
        "--manual-wait",
        type=float,
        default=35.0,
        help="Seconds to wait before dump (manual mode).",
    )
    args = parser.parse_args()

    config = load_config(args.config.resolve())
    bundle = str((config.get("app") or {}).get("bundle_id") or "").strip()
    if not bundle:
        print("[error] config app.bundle_id is required", file=sys.stderr)
        return 1

    driver = create_ios_driver(config)
    out_dir = ROOT / "reports" / "debug"
    try:
        if args.mode == "manual":
            try:
                driver.terminate_app(bundle)
            except Exception:
                pass
            driver.activate_app(bundle)
            print(f"[manual] App foregrounded. Navigate to the meal result screen; sleeping {args.manual_wait}s …")
            time.sleep(args.manual_wait)
            _dump(driver, out_dir, tag="manual")
            return 0

        page = FoodzillaPage(driver, config)
        page.open_app()
        time.sleep(2.0)
        page.tap_scan_or_upload()
        time.sleep(2.5)
        img = resolve_path(args.image, ROOT)
        if not img.is_file():
            print(f"[error] image not found: {img}", file=sys.stderr)
            return 1
        page.select_image(args.image.strip())
        print(f"[automated] Waiting {args.analyze_wait}s for analysis UI …")
        time.sleep(args.analyze_wait)
        _dump(driver, out_dir, tag="after_analysis")
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
