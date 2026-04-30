# Replace TODO accessibility IDs / iOS class chain / predicates with values from
# Appium Inspector or Xcode for your FoodZilla build.

from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

# --- Required (rename values only; keep names for page base) ---
SCAN_ENTRY = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_SCAN_ENTRY")
RESULT_PANEL = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_RESULT_PANEL")

# Backward-compatible aliases used by older snippets
PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL

# --- Optional: photo picker chain (set when you map the UI) ---
PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = None
PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = None
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None
SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = None

# --- Optional: split labels if the app shows detection vs classification separately ---
RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None
