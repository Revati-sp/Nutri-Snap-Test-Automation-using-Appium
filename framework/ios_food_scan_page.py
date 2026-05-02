"""
Reusable iOS flow for food CV apps: foreground app → scan/upload → optional photo picker → read result.

Each app supplies a `locators` module with at least `SCAN_ENTRY` and `RESULT_PANEL` (or legacy
`PLACEHOLDER_*` aliases). Optional locators extend the flow without hardcoding app internals here.
"""

from __future__ import annotations

import re
import time
from types import ModuleType
from typing import Any, Mapping, Optional

from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException

from framework.base_driver import safe_wait_until_present, safe_wait_until_visible
from framework.config_loader import get_nested
from framework.logger import get_logger
from framework.utils import resolve_path

logger = get_logger(__name__)

_TC_INDEX_RE = re.compile(r"TC0*(\d+)", re.IGNORECASE)


def _click_resilient(
    driver: WebDriver,
    locator: tuple[str, str],
    *,
    timeout: float = 15.0,
    use_present: bool = False,
    retries: int = 2,
) -> bool:
    """Wait for an element and click it, retrying on StaleElementReferenceException.

    iOS frequently re-renders views during transitions (e.g. right after activate_app, sheet
    dismissal, or async layout passes). The handle returned by the first wait can expire before
    .click() lands, so we re-find the element and retry.

    Returns True on successful click, False if the element never appeared.
    """
    finder = safe_wait_until_present if use_present else safe_wait_until_visible
    for attempt in range(retries + 1):
        el = finder(driver, locator, timeout=timeout)
        if not el:
            return False
        try:
            el.click()
            return True
        except StaleElementReferenceException:
            logger.info(
                "click on %r got stale element (attempt %d/%d) — re-finding",
                locator,
                attempt + 1,
                retries + 1,
            )
            time.sleep(0.5)
    return False


def _index_to_picker_time_label(idx_1_based: int) -> str:
    """Convert a 1-based TC index to the iOS PHPicker VoiceOver label that
    `scripts/stamp_test_images.py` arranges for each test image.

    Anchor: TC01 -> "Photo, 01 January, 12:00 PM". Each subsequent TC adds 10 minutes:
        TC01 -> 12:00 PM,  TC07 -> 1:00 PM,  TC13 -> 2:00 PM, ... TC31 -> 5:00 PM.
    """
    minute_offset = (idx_1_based - 1) * 10
    base_hour_24 = 12 + minute_offset // 60  # noon + N hours
    minute = minute_offset % 60
    base_hour_24 %= 24
    if base_hour_24 == 0:
        h_disp, suffix = 12, "AM"
    elif base_hour_24 < 12:
        h_disp, suffix = base_hour_24, "AM"
    elif base_hour_24 == 12:
        h_disp, suffix = 12, "PM"
    else:
        h_disp, suffix = base_hour_24 - 12, "PM"
    return f"Photo, 01 January, {h_disp}:{minute:02d} {suffix}"


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

    def _dump_debug_state(self, tag: str) -> None:
        """Best-effort: write current page_source + a screenshot to reports/debug/ for triage.

        Called when an expected locator can't be found, so we can compare the live DOM against
        what dump_picker_source.py captured offline.
        """
        from datetime import datetime, timezone
        from pathlib import Path

        out_dir = Path(__file__).resolve().parent.parent / "reports" / "debug"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_tag = "".join(c if c.isalnum() else "_" for c in tag)[:40] or "state"
        try:
            xml = self.driver.page_source
            (out_dir / f"{safe_tag}_{ts}.xml").write_text(xml, encoding="utf-8")
            logger.info("%s: dumped page_source -> reports/debug/%s_%s.xml", self._log, safe_tag, ts)
        except Exception:
            logger.warning("%s: page_source dump failed", self._log, exc_info=True)
        try:
            self.driver.get_screenshot_as_file(str(out_dir / f"{safe_tag}_{ts}.png"))
            logger.info("%s: dumped screenshot -> reports/debug/%s_%s.png", self._log, safe_tag, ts)
        except Exception:
            logger.warning("%s: screenshot dump failed", self._log, exc_info=True)

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

    def reset_app(self) -> None:
        """Terminate and re-activate the AUT to guarantee a clean home-screen state for the next test.

        Called between rows in batch mode so we don't carry over result screens, modal sheets,
        or stuck pickers from the previous case. A short settle delay follows the relaunch
        because iOS keeps mutating the view hierarchy for ~1-2s after the splash, which causes
        StaleElementReferenceException on the very first tap if we don't wait.
        """
        bundle = str(get_nested(self._config, "app", "bundle_id", default="") or "")
        if not bundle:
            return
        try:
            self.driver.terminate_app(bundle)
            logger.info("%s: terminated app (bundle_id=%s)", self._log, bundle)
        except Exception:
            logger.warning("%s: terminate_app(%s) raised", self._log, bundle, exc_info=True)
        try:
            self.driver.activate_app(bundle)
            logger.info("%s: re-activated app (bundle_id=%s)", self._log, bundle)
        except Exception:
            logger.warning("%s: activate_app(%s) raised", self._log, bundle, exc_info=True)
        time.sleep(2.0)

    def tap_scan_or_upload(self) -> None:
        """Step 1–2: open the scan / camera / upload entry (one primary control or first of a chain)."""
        scan_loc = self._scan_locator()
        if not scan_loc:
            logger.warning("%s: define SCAN_ENTRY (or PLACEHOLDER_BUTTON) in locators.py", self._log)
            return
        if _click_resilient(self.driver, scan_loc, timeout=25.0):
            logger.info("%s: tapped scan/upload control", self._log)
            time.sleep(2.5)  # Action sheet animates in.
        else:
            logger.warning("%s: scan/upload control not clicked (check locator / flow)", self._log)
            self._dump_debug_state(tag="scan_entry_not_clicked")

        alt = getattr(self._loc, "SCAN_SECONDARY_TAP", None)
        if alt:
            # Longer timeout: action sheet sometimes takes 5-10s to fully populate options on
            # cold app launch (Lose It! refreshes Snap It availability against its server).
            if _click_resilient(self.driver, alt, timeout=20.0):
                logger.info("%s: tapped secondary scan step", self._log)
                time.sleep(2.0)  # Camera screen takes time to come up.
            else:
                logger.warning("%s: secondary scan step (%r) not clicked", self._log, alt)
                # Dump now so we can see exactly what's on screen (sheet open? closed? wrong text?)
                self._dump_debug_state(tag="snap_it_not_clicked")

    def _resolve_cell_locator(self, image_path: str) -> Optional[tuple[str, str]]:
        """Build a per-row cell locator.

        Two flavors supported in `locators.py`:
          A. Static `PHOTO_PICKER_CELL = (by, value)` — used as-is for every row.
          B. Templated `PHOTO_PICKER_CELL_TEMPLATE = (by, "...{tag}...")` — supported substitution tags:
             * ``{INDEX}``      -> 1-based TC number (e.g. "TC07.jpg" -> 7).
             * ``{TIME_LABEL}`` -> EXIF-derived VoiceOver label, e.g. "Photo, 01 January, 1:00 PM".
        ``{TIME_LABEL}`` is the recommended form for iOS PHPicker because the cell's `label`
        attribute is stable across scrolling/filtering, while ordinal `[INDEX]` breaks the moment
        the grid scrolls or the user switches album.
        """
        tmpl = getattr(self._loc, "PHOTO_PICKER_CELL_TEMPLATE", None)
        if tmpl:
            by, fmt = tmpl
            m = _TC_INDEX_RE.search(image_path or "")
            if not m:
                logger.warning(
                    "%s: PHOTO_PICKER_CELL_TEMPLATE set but no TC<NN> id found in %r",
                    self._log,
                    image_path,
                )
                return None
            idx = int(m.group(1))
            value = fmt.replace("{INDEX}", str(idx)).replace(
                "{TIME_LABEL}", _index_to_picker_time_label(idx)
            )
            return (by, value)
        return getattr(self._loc, "PHOTO_PICKER_CELL", None)

    def _picker_cell_coordinate(self, idx_1_based: int) -> Optional[tuple[int, int]]:
        """Compute the screen coordinate for the Nth picker cell, using grid geometry observed
        from `reports/debug/step_trace/step05_after_album_row_ok.xml` for iOS 26 PHPicker:

            - grid origin (top-left of cell 0): x=0, y=127
            - 3 columns, ~130px wide each
            - rows ~130px tall
            - cells are zero-indexed left-to-right, top-to-bottom

        Returns the center point of the requested cell, or None if the input is invalid.
        Cells beyond the first ~18 require scrolling first; this helper assumes the cell is
        already scrolled into view (TC01-TC18 fit on screen at iPhone 13 size).
        """
        if idx_1_based < 1:
            return None
        zero_based = idx_1_based - 1
        col = zero_based % 3
        row = zero_based // 3
        cell_w = 130
        cell_h = 130
        origin_y = 127
        x_center = col * cell_w + cell_w // 2
        y_center = origin_y + row * cell_h + cell_h // 2
        return (x_center, y_center)

    def _tap_at(self, x: int, y: int) -> bool:
        """Send a single tap at absolute screen coordinates via the W3C Actions API.

        Used as a fallback when a picker cell is in the DOM but Appium's predicate/class-chain
        matchers can't return it because of iOS 26 PHPicker's `accessible="false"` parent
        containers. We compute coordinates from the known grid layout instead.
        """
        try:
            from selenium.webdriver.common.actions import interaction
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput

            finger = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(self.driver, mouse=finger)
            actions.pointer_action.move_to_location(x, y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.05)
            actions.pointer_action.pointer_up()
            actions.perform()
            logger.info("%s: coordinate-tapped (%d, %d)", self._log, x, y)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: coordinate tap (%d, %d) failed: %r", self._log, x, y, exc)
            return False

    def select_image(self, image_path: str) -> None:
        """
        Step 3: choose the test image from the iOS PHPicker.

        Flow (driven by whichever locators are present in the app's `locators.py`):
          1. Tap `PHOTO_LIBRARY_BUTTON`             — open the system PHPicker.
          2. Tap `PHOTO_PICKER_COLLECTIONS_TAB`     — switch to the album list (PHPicker remembers tab).
          3. Tap `PHOTO_ALBUM_ROW`                  — open NutriSnapTests (or whichever album).
          4. Tap the cell matching this row         — derived from `PHOTO_PICKER_CELL_TEMPLATE` and TC id.

        The `image_path` value is used both for logging and for parsing the TC number that picks the
        right cell (so cell [N] == TC<N>.jpg in the on-device album).
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
            if _click_resilient(self.driver, lib_btn, timeout=12.0):
                logger.info("%s: chose photo library / gallery option", self._log)
                time.sleep(2.5)  # PHPicker has a noticeable present animation; wait before next tap.
            else:
                logger.warning("%s: photo library button (%r) not clicked", self._log, lib_btn)

        tab = getattr(self._loc, "PHOTO_PICKER_COLLECTIONS_TAB", None)
        if tab:
            if _click_resilient(self.driver, tab, timeout=8.0):
                logger.info("%s: switched to picker Collections tab", self._log)
                time.sleep(2.5)
            else:
                logger.warning("%s: collections tab (%r) not clicked", self._log, tab)

        album = getattr(self._loc, "PHOTO_ALBUM_ROW", None)
        if album:
            if _click_resilient(self.driver, album, timeout=20.0):
                logger.info("%s: opened album row", self._log)
                time.sleep(2.5)  # PHPicker grid populates async; wait before polling cells.
            else:
                logger.warning("%s: album row (%r) not clicked", self._log, album)
                self._dump_debug_state(tag="album_row_not_clicked")

        cell = self._resolve_cell_locator(rel)
        cell_clicked = False
        if cell:
            # PHPicker grid cells report `visible="false"` even when rendered/tappable, so wait
            # on presence-in-DOM rather than visibility (the latter times out on virtualized lists).
            if _click_resilient(self.driver, cell, timeout=10.0, use_present=True):
                logger.info("%s: selected picker cell %r", self._log, cell[1])
                cell_clicked = True
            else:
                logger.info(
                    "%s: cell locator %r not findable via XCUITest queries (iOS 26 PHPicker "
                    "marks parent containers accessible=false); falling back to coordinate tap.",
                    self._log,
                    cell,
                )

        # Coordinate-tap fallback: iOS 26 PHPicker hides cells from Appium's element finder,
        # so we tap the calculated center of the Nth cell. Works for TC01-TC18 (the first
        # ~18 cells visible without scrolling).
        if not cell_clicked:
            m = _TC_INDEX_RE.search(rel)
            if not m:
                logger.warning("%s: cannot derive TC index from %r for coordinate tap", self._log, rel)
                self._dump_debug_state(tag="cell_no_tc_index")
                return
            idx = int(m.group(1))
            coord = self._picker_cell_coordinate(idx)
            if not coord:
                logger.warning("%s: could not compute coordinate for TC index %d", self._log, idx)
                self._dump_debug_state(tag="cell_no_coord")
                return
            x, y = coord
            if not self._tap_at(x, y):
                self._dump_debug_state(tag="cell_tap_failed")
                return
            logger.info("%s: tapped picker cell TC%02d at (%d, %d)", self._log, idx, x, y)

        confirm = getattr(self._loc, "PHOTO_CONFIRM_BUTTON", None)
        if confirm:
            if _click_resilient(self.driver, confirm, timeout=12.0):
                logger.info("%s: confirmed photo selection", self._log)

        if not lib_btn and not cell:
            logger.warning(
                "%s: select_image — set PHOTO_LIBRARY_BUTTON / PHOTO_PICKER_CELL[_TEMPLATE] in "
                "locators.py to drive the iOS picker, or implement an app-specific path. "
                "Referenced file: %s",
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
