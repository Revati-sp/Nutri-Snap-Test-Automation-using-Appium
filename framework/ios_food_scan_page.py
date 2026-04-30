"""
Reusable iOS flow for food CV apps: foreground app → scan/upload → optional photo picker → read result.

Each app supplies a `locators` module with at least `SCAN_ENTRY` and `RESULT_PANEL` (or legacy
`PLACEHOLDER_*` aliases). Optional locators extend the flow without hardcoding app internals here.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any, Mapping, Optional

from appium.webdriver.webdriver import WebDriver

from framework.base_driver import safe_wait_until_visible
from framework.config_loader import get_nested
from framework.logger import get_logger
from framework.utils import resolve_path

logger = get_logger(__name__)


class IosFoodScanPageBase:
    """Wire your real locators in `apps/<app>/locators.py`; keep page subclasses as thin wrappers."""

    def __init__(
        self,
        driver: WebDriver,
        config: Optional[Mapping[str, Any]],
        loc: ModuleType,
        app_log_name: str,
    ) -> None:
        self.driver = driver
        self._config = dict(config or {})
        self._loc = loc
        self._log = app_log_name

    def _scan_locator(self) -> Optional[tuple[str, str]]:
        loc = self._loc
        return getattr(loc, "SCAN_ENTRY", None) or getattr(loc, "PLACEHOLDER_BUTTON", None)

    def _result_locator(self) -> Optional[tuple[str, str]]:
        loc = self._loc
        return getattr(loc, "RESULT_PANEL", None) or getattr(loc, "PLACEHOLDER_RESULT", None)

    def open_app(self) -> None:
        """Bring the AUT to the foreground (session is already created with bundle_id in caps)."""
        bundle = str(get_nested(self._config, "app", "bundle_id", default="") or "")
        if bundle:
            try:
                self.driver.activate_app(bundle)
            except Exception:
                logger.exception("%s: activate_app(%s) failed", self._log, bundle)
        logger.info("%s: open_app (bundle_id=%s)", self._log, bundle or "(session default)")

    def tap_scan_or_upload(self) -> None:
        """Step 1–2: open the scan / camera / upload entry (one primary control or first of a chain)."""
        scan_loc = self._scan_locator()
        if not scan_loc:
            logger.warning("%s: define SCAN_ENTRY (or PLACEHOLDER_BUTTON) in locators.py", self._log)
            return
        el = safe_wait_until_visible(self.driver, scan_loc, timeout=25.0)
        if el:
            el.click()
            logger.info("%s: tapped scan/upload control", self._log)
        else:
            logger.warning("%s: scan/upload control not visible (check locator / flow)", self._log)

        alt = getattr(self._loc, "SCAN_SECONDARY_TAP", None)
        if alt:
            el2 = safe_wait_until_visible(self.driver, alt, timeout=8.0)
            if el2:
                el2.click()
                logger.info("%s: tapped secondary scan step", self._log)

    def select_image(self, image_path: str) -> None:
        """
        Step 3: choose the test image. Repo paths are resolved from project root.

        Typical real-device pattern (you complete with locators):
        1) Sheet appears → tap **Photo Library** / **Choose Photos** (`PHOTO_LIBRARY_BUTTON`).
        2) Picker grid → tap a cell (`PHOTO_PICKER_CELL`) or album row (`PHOTO_ALBUM_ROW`).

        If the app only accepts camera live capture, pre-seed the camera roll and tap that asset,
        or use an app-specific file/import API once discovered in Inspector.
        """
        rel = (image_path or "").strip()
        if not rel:
            return
        path = resolve_path(rel)
        if not path.is_file():
            logger.warning("%s: image file not found: %s", self._log, path)
            return

        lib_btn = getattr(self._loc, "PHOTO_LIBRARY_BUTTON", None)
        if lib_btn:
            el = safe_wait_until_visible(self.driver, lib_btn, timeout=12.0)
            if el:
                el.click()
                logger.info("%s: chose photo library / gallery option", self._log)

        album = getattr(self._loc, "PHOTO_ALBUM_ROW", None)
        if album:
            el = safe_wait_until_visible(self.driver, album, timeout=10.0)
            if el:
                el.click()
                logger.info("%s: opened album row", self._log)

        cell = getattr(self._loc, "PHOTO_PICKER_CELL", None)
        if cell:
            el = safe_wait_until_visible(self.driver, cell, timeout=18.0)
            if el:
                el.click()
                logger.info("%s: selected picker cell / thumbnail", self._log)
                return

        if not lib_btn and not cell:
            logger.warning(
                "%s: select_image — set PHOTO_LIBRARY_BUTTON / PHOTO_PICKER_CELL in locators.py "
                "to drive the iOS picker, or implement an app-specific path. Referenced file: %s",
                self._log,
                path,
            )

    def read_result_text(self) -> str:
        """
        Step 4: read on-screen model output after analysis.

        Prefer a single `RESULT_PANEL` label whose `text` matches Deliverable 2B `expected_output`.
        Alternatively set `RESULT_DETECTION` + `RESULT_CLASSIFICATION`; this base joins them as
        ``\"detection, classification\"`` (comma-space), which matches many 2B rows.
        """
        det_loc = getattr(self._loc, "RESULT_DETECTION", None)
        cls_loc = getattr(self._loc, "RESULT_CLASSIFICATION", None)
        if det_loc and cls_loc:
            d_el = safe_wait_until_visible(self.driver, det_loc, timeout=60.0)
            c_el = safe_wait_until_visible(self.driver, cls_loc, timeout=15.0)
            parts: list[str] = []
            if d_el and (d_el.text or "").strip():
                parts.append((d_el.text or "").strip())
            if c_el and (c_el.text or "").strip():
                parts.append((c_el.text or "").strip())
            if parts:
                return ", ".join(parts)

        res = self._result_locator()
        if not res:
            logger.warning("%s: define RESULT_PANEL (or PLACEHOLDER_RESULT) in locators.py", self._log)
            return ""
        el = safe_wait_until_visible(self.driver, res, timeout=60.0)
        if el and el.text:
            return el.text.strip()
        return ""

    def read_model_output(self) -> str:
        """String compared to CSV `expected_output` (trimmed / normalized in validator)."""
        return self.read_result_text()
