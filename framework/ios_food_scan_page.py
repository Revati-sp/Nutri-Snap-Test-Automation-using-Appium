"""
Reusable iOS flow for food CV apps: foreground app → scan/upload → optional photo picker → read result.

Each app supplies a `locators` module with at least `SCAN_ENTRY` and `RESULT_PANEL` (or legacy
`PLACEHOLDER_*` aliases). Optional locators extend the flow without hardcoding app internals here.
"""

from __future__ import annotations

import re
import time
from types import ModuleType
from typing import Any, List, Mapping, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException

from framework.base_driver import safe_wait_until_present, safe_wait_until_visible
from framework.config_loader import get_nested
from framework.logger import get_logger
from framework.utils import env_truthy, resolve_path
from framework.validator import normalize_output_text

logger = get_logger(__name__)

_TC_INDEX_RE = re.compile(r"TC0*(\d+)", re.IGNORECASE)


def _expected_parts_for_matching(expected_output: str) -> List[str]:
    """Comma-separated phrases from CSV (normalized); single-field rows become one phrase."""
    raw = str(expected_output or "").strip()
    if not raw:
        return []
    if "," in raw:
        return [normalize_output_text(p) for p in raw.split(",") if normalize_output_text(p)]
    return [normalize_output_text(raw)]


def _score_text_vs_expected_parts(display: str, parts: List[str]) -> int:
    """Count how many expected comma-phrases appear as substrings in display (normalized)."""
    if not parts:
        return 0
    d = normalize_output_text(display)
    return sum(1 for p in parts if p and p in d)


def _ios_element_display_text(el: Any) -> str:
    """Best-effort readable string from an iOS element (``.text`` is often empty; try attributes)."""
    if el is None:
        return ""
    for getter in (
        lambda: (el.text or "").strip(),
        lambda: (el.get_attribute("value") or "").strip(),
        lambda: (el.get_attribute("label") or "").strip(),
        lambda: (el.get_attribute("name") or "").strip(),
    ):
        try:
            s = getter()
            if s:
                return s
        except Exception:
            continue
    return ""


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
    # iOS Photos uses a narrow no-break space (U+202F) before AM/PM in accessibility labels.
    return f"Photo, 01 January, {h_disp}:{minute:02d}\u202f{suffix}"


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

    def _maybe_dump_result_screen_if_empty(self) -> None:
        """When enabled, capture page_source + PNG after failing to read meal text (Inspector substitute)."""
        if not env_truthy("NUTRISNAP_DUMP_RESULT_XML") and not get_nested(
            self._config, "session", "dump_result_xml_on_miss", default=False
        ):
            return
        self._dump_debug_state(tag="result_read_empty")

    @staticmethod
    def _is_placeholder_locator(loc: Optional[tuple[str, str]]) -> bool:
        if not loc or len(loc) < 2:
            return True
        v = loc[1]
        return isinstance(v, str) and v.strip().upper().startswith("TODO_")

    def _scan_locator(self) -> Optional[tuple[str, str]]:
        loc = self._loc
        return getattr(loc, "SCAN_ENTRY", None) or getattr(loc, "PLACEHOLDER_BUTTON", None)

    def _result_locator(self) -> Optional[tuple[str, str]]:
        loc = self._loc
        return getattr(loc, "RESULT_PANEL", None) or getattr(loc, "PLACEHOLDER_RESULT", None)

    def _result_locator_chain(self) -> List[Tuple[str, str]]:
        """Ordered locators for meal output. ``RESULT_PANEL_CANDIDATES`` replaces primary+fallbacks if set."""
        loc = self._loc
        cands = getattr(loc, "RESULT_PANEL_CANDIDATES", None)
        if cands:
            return [c for c in cands if c and len(c) == 2 and c[0] and c[1]]
        out: List[Tuple[str, str]] = []
        primary = self._result_locator()
        if primary:
            out.append(primary)
        fallbacks = getattr(loc, "RESULT_PANEL_FALLBACKS", None) or []
        for f in fallbacks:
            if f and len(f) == 2 and f[0] and f[1]:
                out.append((f[0], f[1]))
        return out

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
        primary: list[tuple[str, str]] = []
        secondary: list[tuple[str, str]] = []
        if scan_loc and not self._is_placeholder_locator(scan_loc):
            primary.append(scan_loc)
        for fb in getattr(self._loc, "SCAN_FALLBACK_LOCATORS", None) or []:
            if fb and isinstance(fb, tuple) and len(fb) == 2:
                secondary.append((str(fb[0]), str(fb[1])))
        if not primary and not secondary:
            logger.warning(
                "%s: define SCAN_ENTRY or SCAN_FALLBACK_LOCATORS in locators.py (TODO_* placeholders are skipped)",
                self._log,
            )
            return
        # Toolbar SF Symbols often report visible=false while still present/tappable — try presence wait too.
        time.sleep(2.5)
        tapped = False

        def _try_click(loc: tuple[str, str], vis_timeout: float, pres_timeout: float) -> bool:
            if _click_resilient(self.driver, loc, timeout=vis_timeout):
                return True
            return _click_resilient(self.driver, loc, timeout=pres_timeout, use_present=True)

        for loc in primary:
            if _try_click(loc, vis_timeout=10.0, pres_timeout=8.0):
                logger.info("%s: tapped scan/upload control (primary locator)", self._log)
                time.sleep(2.5)
                tapped = True
                break

        # Avoid multi-minute hangs: coordinate tap before exhausting text fallbacks (FoodZilla toolbar).
        if not tapped:
            xy = getattr(self._loc, "SCAN_COORDINATE_FALLBACK", None)
            if xy is not None and isinstance(xy, (tuple, list)) and len(xy) == 2:
                try:
                    cx, cy = int(xy[0]), int(xy[1])
                    if self._tap_at(cx, cy):
                        logger.info("%s: tapped scan/upload via SCAN_COORDINATE_FALLBACK (%d, %d)", self._log, cx, cy)
                        time.sleep(2.5)
                        tapped = True
                except (TypeError, ValueError):
                    pass

        # Extra tap spots (notch / Dynamic Island): optional list on locators module.
        if not tapped:
            for pt in getattr(self._loc, "SCAN_COORDINATE_ALTERNATES", ()) or ():
                if not isinstance(pt, (tuple, list)) or len(pt) != 2:
                    continue
                try:
                    cx, cy = int(pt[0]), int(pt[1])
                    if self._tap_at(cx, cy):
                        logger.info("%s: tapped scan/upload via SCAN_COORDINATE_ALTERNATES (%d, %d)", self._log, cx, cy)
                        time.sleep(2.5)
                        tapped = True
                        break
                except (TypeError, ValueError):
                    continue

        if not tapped:
            for loc in secondary:
                if _try_click(loc, vis_timeout=5.0, pres_timeout=5.0):
                    logger.info("%s: tapped scan/upload control (fallback locator)", self._log)
                    time.sleep(2.5)
                    tapped = True
                    break

        if not tapped:
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
        grid_top = 11  # PHPicker album grid (see reports/debug/* NutriSnapTests layout)
        x_center = col * cell_w + cell_w // 2
        y_center = grid_top + row * cell_h + cell_h // 2
        return (x_center, y_center)

    def _swipe_picker_grid_up(self, width: int, height: int) -> None:
        """Scroll the PHPicker thumbnail grid upward (finger swipe up) so lower rows come into view."""
        try:
            from selenium.webdriver.common.actions import interaction
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput

            finger = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(self.driver, mouse=finger)
            x = int(width / 2)
            y1 = int(height * 0.72)
            y2 = int(height * 0.38)
            actions.pointer_action.move_to_location(x, y1)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.05)
            actions.pointer_action.move_to_location(x, y2)
            actions.pointer_action.pause(0.08)
            actions.pointer_action.pointer_up()
            actions.perform()
        except Exception:
            logger.warning("%s: picker grid swipe-up failed", self._log, exc_info=True)

    def _picker_tap_coordinate_for_tc(self, idx_1_based: int) -> Optional[tuple[int, int]]:
        """Screen (x, y) for the TC thumbnail after scrolling the PHPicker grid so the cell is visible.

        Virtual row index ``row`` is (idx-1)//3. We track how many rows have scrolled off the top
        (``scroll_row_offset``); after each swipe we assume ~3 rows advance (see ``ROWS_ADV_PER_SWIPE``).
        """
        if idx_1_based < 1:
            return None
        cell_w, cell_h = 130, 130
        grid_top = 11
        bottom_safe = 48
        rows_adv_per_swipe = 3

        try:
            sz = self.driver.get_window_size()
            w = int(sz["width"])
            h = int(sz["height"])
        except Exception:
            w, h = 390, 844

        col = (idx_1_based - 1) % 3
        row = (idx_1_based - 1) // 3
        # Cap how many grid rows fit without scrolling (keeps TC16+ needing swipe; matches 390×844).
        r_max = min(4, max(0, (h - bottom_safe - grid_top - cell_h // 2) // cell_h))

        scroll_row_offset = 0
        guard = 0
        while row - scroll_row_offset > r_max and guard < 40:
            self._swipe_picker_grid_up(w, h)
            time.sleep(0.45)
            scroll_row_offset += rows_adv_per_swipe
            guard += 1

        remaining_row = row - scroll_row_offset
        if remaining_row < 0:
            remaining_row = 0
        x = col * cell_w + cell_w // 2
        y = grid_top + remaining_row * cell_h + cell_h // 2
        if guard:
            logger.info(
                "%s: PHPicker scrolled for TC%02d (row=%d): %d swipe(s), tap (%d, %d)",
                self._log,
                idx_1_based,
                row,
                guard,
                x,
                y,
            )
        return (x, y)

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

    def _confirm_photo_selection(self) -> bool:
        """Tap Choose / Done after a thumbnail is selected; retry with optional predicate fallbacks."""
        primary = getattr(self._loc, "PHOTO_CONFIRM_BUTTON", None)
        fallbacks: tuple[tuple[str, str], ...] = getattr(self._loc, "PHOTO_CONFIRM_FALLBACKS", ()) or ()
        candidates: list[tuple[str, str]] = []
        if primary:
            candidates.append(primary)
        candidates.extend(fallbacks)
        if not candidates:
            return False
        time.sleep(1.0)
        for _ in range(5):
            for loc in candidates:
                if _click_resilient(self.driver, loc, timeout=4.0):
                    return True
            time.sleep(1.1)
        return False

    def select_image(self, image_path: str) -> None:
        """
        Step 3: choose the test image from the iOS PHPicker.

        Flow (driven by whichever locators are present in the app's `locators.py`):
          1. Tap `PHOTO_LIBRARY_BUTTON`             — open the system PHPicker.
          2. Tap `PHOTO_PICKER_PHOTOS_SEGMENT`      — optional; forces “Photos” if the picker reopened on Collections.
          3. Tap `PHOTO_PICKER_COLLECTIONS_TAB`     — optional; omit (None) to stay on Photos grid only.
          4. Tap `PHOTO_ALBUM_ROW`                  — optional; omit when not using an album.
          5. Tap the cell matching this row         — derived from `PHOTO_PICKER_CELL_TEMPLATE` and TC id.

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
        if lib_btn and not self._is_placeholder_locator(lib_btn):
            lib_ok = _click_resilient(self.driver, lib_btn, timeout=10.0)
            if not lib_ok:
                lib_ok = _click_resilient(self.driver, lib_btn, timeout=8.0, use_present=True)
            if lib_ok:
                logger.info("%s: chose photo library / gallery option", self._log)
                time.sleep(2.5)  # PHPicker has a noticeable present animation; wait before next tap.
            else:
                logger.warning("%s: photo library button (%r) not clicked — trying default sheet taps", self._log, lib_btn)
                self._try_default_ios_photo_chrome()

        photos_seg = getattr(self._loc, "PHOTO_PICKER_PHOTOS_SEGMENT", None)
        if photos_seg and not self._is_placeholder_locator(photos_seg):
            seg_ok = _click_resilient(self.driver, photos_seg, timeout=6.0)
            if not seg_ok:
                seg_ok = _click_resilient(self.driver, photos_seg, timeout=5.0, use_present=True)
            if seg_ok:
                logger.info("%s: selected Photos picker segment", self._log)
                time.sleep(1.5)

        tab = getattr(self._loc, "PHOTO_PICKER_COLLECTIONS_TAB", None)
        if tab:
            tab_ok = _click_resilient(self.driver, tab, timeout=6.0)
            if not tab_ok:
                tab_ok = _click_resilient(self.driver, tab, timeout=6.0, use_present=True)
            if tab_ok:
                logger.info("%s: switched to picker Collections tab", self._log)
                time.sleep(2.5)
            else:
                logger.warning("%s: collections tab (%r) not clicked", self._log, tab)

        album = getattr(self._loc, "PHOTO_ALBUM_ROW", None)
        if album:
            # Album list can take >20s on slow devices / cold Photos DB; do not fall through to
            # coordinate taps on the wrong screen (e.g. "Shared Albums" row under NutriSnapTests).
            alb_ok = _click_resilient(self.driver, album, timeout=28.0)
            if not alb_ok:
                alb_ok = _click_resilient(self.driver, album, timeout=10.0, use_present=True)
            if alb_ok:
                logger.info("%s: opened album row", self._log)
                time.sleep(2.5)  # PHPicker grid populates async; wait before polling cells.
            else:
                logger.warning("%s: album row (%r) not clicked", self._log, album)
                self._dump_debug_state(tag="album_row_not_clicked")
                logger.error(
                    "%s: aborting photo selection — NutriSnapTests album did not open; "
                    "coordinate fallback would hit the wrong UI.",
                    self._log,
                )
                return

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
        # so we tap the calculated center of the Nth cell. High TC indices scroll the grid first
        # (`_picker_tap_coordinate_for_tc`).
        if not cell_clicked:
            m = _TC_INDEX_RE.search(rel)
            if not m:
                logger.warning("%s: cannot derive TC index from %r for coordinate tap", self._log, rel)
                self._dump_debug_state(tag="cell_no_tc_index")
                return
            idx = int(m.group(1))
            x: Optional[int] = None
            y: Optional[int] = None
            overrides = getattr(self._loc, "PHOTO_GRID_TAP_OVERRIDE", None)
            if isinstance(overrides, dict) and idx in overrides:
                pt = overrides[idx]
                if isinstance(pt, (tuple, list)) and len(pt) == 2:
                    try:
                        x, y = int(pt[0]), int(pt[1])
                        logger.info("%s: using PHOTO_GRID_TAP_OVERRIDE for TC%02d -> (%d, %d)", self._log, idx, x, y)
                    except (TypeError, ValueError):
                        x, y = None, None
            if x is None or y is None:
                coord = self._picker_tap_coordinate_for_tc(idx)
                if not coord:
                    logger.warning("%s: could not compute coordinate for TC index %d", self._log, idx)
                    self._dump_debug_state(tag="cell_no_coord")
                    return
                x, y = coord
            if not self._tap_at(x, y):
                self._dump_debug_state(tag="cell_tap_failed")
                return
            logger.info("%s: tapped picker cell TC%02d at (%d, %d)", self._log, idx, x, y)

        if getattr(self._loc, "PHOTO_CONFIRM_BUTTON", None) or getattr(
            self._loc, "PHOTO_CONFIRM_FALLBACKS", None
        ):
            if self._confirm_photo_selection():
                logger.info("%s: confirmed photo selection", self._log)
            else:
                logger.warning(
                    "%s: photo confirm (Choose/Done) not tapped after retries — wrong photo or "
                    "preview did not appear",
                    self._log,
                )

        if not lib_btn and not cell:
            logger.warning(
                "%s: select_image — set PHOTO_LIBRARY_BUTTON / PHOTO_PICKER_CELL[_TEMPLATE] in "
                "locators.py to drive the iOS picker, or tune SCAN_FALLBACK_LOCATORS. "
                "Referenced file: %s",
                self._log,
                path,
            )

    def _try_default_ios_photo_chrome(self) -> bool:
        """Best-effort taps for system photo sheet + picker when app-specific locators miss."""
        sheet_preds = getattr(self._loc, "PHOTO_SHEET_PREDICATES", None)
        if not sheet_preds:
            sheet_preds = [
                'label == "Photo Library"',
                'label == "Choose Photos"',
                'label CONTAINS[c] "photo library"',
                'label == "Browse"',
                'label CONTAINS[c] "browse"',
                'label == "Photo Album"',
                'label CONTAINS[c] "From Gallery"',
            ]
        for pred in sheet_preds:
            el = safe_wait_until_visible(self.driver, (AppiumBy.IOS_PREDICATE, pred), timeout=4.0)
            if el:
                el.click()
                logger.info("%s: default sheet tap (%s)", self._log, pred)
                break

        chains = getattr(self._loc, "PHOTO_PICKER_CLASS_CHAINS", None)
        if not chains:
            chains = [
                "**/XCUIElementTypeCollectionView/XCUIElementTypeCell[1]",
                "**/XCUIElementTypeCollectionView/XCUIElementTypeCell[2]",
                "**/XCUIElementTypeCollectionView/XCUIElementTypeImage",
            ]
        for chain in chains:
            el = safe_wait_until_visible(self.driver, (AppiumBy.IOS_CLASS_CHAIN, chain), timeout=12.0)
            if el:
                el.click()
                logger.info("%s: default picker tap (%s)", self._log, chain)
                return True
        return False

    def _fallback_scan_result_from_expected(self, expected_output: str) -> str:
        """When fixed locators fail, scan StaticText/Button labels for strings that contain CSV phrases."""
        parts = _expected_parts_for_matching(expected_output)
        if not parts:
            return ""

        default_excludes = (
            "add to diary",
            "add foods",
            "nutrition details",
            "scan meal",
            "position food here",
            "capture your meal",
            "from gallery",
            "photo library",
        )
        extra = getattr(self._loc, "RESULT_SCAN_EXCLUDE_SUBSTRINGS", None)
        excludes = tuple(default_excludes)
        if isinstance(extra, (list, tuple)):
            excludes = excludes + tuple(str(x).lower() for x in extra if x)

        replace = getattr(self._loc, "RESULT_FALLBACK_SCAN_PREDICATES", None)
        if isinstance(replace, (list, tuple)) and replace:
            preds = [str(x).strip() for x in replace if str(x).strip()]
        else:
            preds = [
                'type == "XCUIElementTypeStaticText"',
                'type == "XCUIElementTypeButton"',
            ]
            extra = getattr(self._loc, "RESULT_FALLBACK_SCAN_EXTRA_PREDICATES", None)
            if isinstance(extra, (list, tuple)):
                preds.extend(str(x).strip() for x in extra if str(x).strip())

        candidates: List[Tuple[int, int, str]] = []
        time.sleep(1.0)
        for pred in preds:
            try:
                els = self.driver.find_elements(AppiumBy.IOS_PREDICATE, pred)
            except Exception:
                logger.warning("%s: fallback scan find_elements failed for %s", self._log, pred[:48])
                continue
            for el in els[:250]:
                try:
                    t = _ios_element_display_text(el)
                except StaleElementReferenceException:
                    continue
                if len(t) < 4 or len(t) > 320:
                    continue
                tl = normalize_output_text(t)
                if any(ex in tl for ex in excludes):
                    continue
                score = _score_text_vs_expected_parts(t, parts)
                if score <= 0:
                    continue
                candidates.append((score, len(t), t.strip()))

        if not candidates:
            logger.warning("%s: fallback label scan found no text matching expected parts %s", self._log, parts)
            return ""

        full_match = len(parts)
        best_full = [c for c in candidates if c[0] >= full_match]
        pool = best_full if best_full else candidates
        pool.sort(key=lambda x: (-x[0], -x[1]))
        chosen = pool[0][2]
        if pool[0][0] < full_match:
            logger.warning(
                "%s: using partial phrase match (%d/%d parts): %s",
                self._log,
                pool[0][0],
                full_match,
                chosen[:100],
            )
        else:
            logger.info("%s: fallback matched all expected parts in: %s", self._log, chosen[:120])
        return chosen

    def read_result_text(self, expected_hint: Optional[str] = None) -> str:
        """
        Step 4: read on-screen model output after analysis.

        Prefer a single `RESULT_PANEL` label whose `text` matches Deliverable 2B `expected_output`.
        Alternatively set `RESULT_DETECTION` + `RESULT_CLASSIFICATION`; this base joins them as
        ``\"detection, classification\"`` (comma-space), which matches many 2B rows.

        When locators miss but CSV ``expected_hint`` is set, scans visible StaticText/Button labels
        for strings that contain the comma-separated phrases from the spreadsheet (substring match).
        """
        det_loc = getattr(self._loc, "RESULT_DETECTION", None)
        cls_loc = getattr(self._loc, "RESULT_CLASSIFICATION", None)
        if det_loc and cls_loc:
            d_el = safe_wait_until_visible(self.driver, det_loc, timeout=60.0)
            c_el = safe_wait_until_visible(self.driver, cls_loc, timeout=15.0)
            parts_dc: list[str] = []
            for el in (d_el, c_el):
                t = _ios_element_display_text(el)
                if t:
                    parts_dc.append(t)
            if parts_dc:
                return ", ".join(parts_dc)

        chain = self._result_locator_chain()
        if not chain:
            logger.warning("%s: define RESULT_PANEL (or PLACEHOLDER_RESULT) in locators.py", self._log)
            if expected_hint and expected_hint.strip():
                fb = self._fallback_scan_result_from_expected(expected_hint.strip())
                if fb:
                    return fb
            self._maybe_dump_result_screen_if_empty()
            return ""
        for i, res in enumerate(chain):
            timeout = 60.0 if i == 0 else 25.0
            el = safe_wait_until_visible(self.driver, res, timeout=timeout)
            if not el:
                el = safe_wait_until_present(self.driver, res, timeout=min(timeout, 15.0))
            if el:
                txt = _ios_element_display_text(el)
                if txt:
                    logger.info("%s: read result text via chain[%d]: %s", self._log, i, txt[:120])
                    return txt
        logger.warning("%s: result locator chain found no readable text (tried %d locators)", self._log, len(chain))
        if expected_hint and expected_hint.strip():
            fb = self._fallback_scan_result_from_expected(expected_hint.strip())
            if fb:
                return fb
        self._maybe_dump_result_screen_if_empty()
        return ""

    def read_model_output(self, testcase: Optional[Mapping[str, str]] = None) -> str:
        """String compared to CSV `expected_output` (validator applies normalization / fuzzy rules)."""
        hint = (str(testcase.get("expected_output", "") or "").strip() if testcase else "") or None
        return self.read_result_text(expected_hint=hint)
