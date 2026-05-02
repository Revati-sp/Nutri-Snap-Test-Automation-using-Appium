from typing import Optional, Tuple
from appium.webdriver.common.appiumby import AppiumBy

# Scan entry — the + button on home screen
SCAN_ENTRY = (AppiumBy.ACCESSIBILITY_ID, "photo")

# Result panel — food name on result screen
RESULT_PANEL = (AppiumBy.XPATH, '//XCUIElementTypeOther[contains(@name, "Ume") or contains(@name, "calories, ")]')

# Backward-compatible aliases
PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL

# Photo picker
PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = None
PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = None
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None
SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = None

# Split result labels
RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None
