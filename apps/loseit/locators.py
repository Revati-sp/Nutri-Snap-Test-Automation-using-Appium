# Replace TODO values using Appium Inspector / Xcode for Lose It!.

from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

SCAN_ENTRY = (AppiumBy.ACCESSIBILITY_ID, "TODO_LOSEIT_SCAN_ENTRY")
RESULT_PANEL = (AppiumBy.ACCESSIBILITY_ID, "TODO_LOSEIT_RESULT_PANEL")

PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL

PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = None
PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = None
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None
SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = None

RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None
