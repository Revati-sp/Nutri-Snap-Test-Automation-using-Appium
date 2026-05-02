# FoodZilla — map app-specific controls via Appium Inspector / Xcode on YOUR build.
#
# Framework contract (`framework/ios_food_scan_page.py`):
#   Required: SCAN_ENTRY, RESULT_PANEL (or legacy PLACEHOLDER_* aliases).
#   Optional: SCAN_SECONDARY_TAP, full PHPicker chain, PHOTO_CONFIRM_BUTTON,
#             RESULT_DETECTION + RESULT_CLASSIFICATION (split labels).
#
# Shared test assets use album "NutriSnapTests" and EXIF-based picker labels;
# see `scripts/stamp_test_images.py` and PHOTO_PICKER_CELL_TEMPLATE below.

from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

# --- Required (replace TODO_* using Inspector — names must stay SCAN_ENTRY / RESULT_PANEL) ---
# Primary control that starts scan / camera / upload from FoodZilla’s main flow.
SCAN_ENTRY = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_SCAN_ENTRY")

# Single element whose text matches Deliverable 2B combined output, OR use RESULT_* split pair.
RESULT_PANEL = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_RESULT_PANEL")

PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL

# --- Optional: second tap after SCAN_ENTRY (action sheet / mode picker) ---
SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = None

# --- Optional: bridge into iOS PHPicker (gallery icon on FoodZilla’s camera / capture UI) ---
PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = None

# --- Shared PHPicker navigation (system UI + team album — usually same across apps) ---
PHOTO_PICKER_COLLECTIONS_TAB: Optional[Tuple[str, str]] = (
    AppiumBy.ACCESSIBILITY_ID,
    "Collections",
)

PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "NutriSnapTests"',
)

# Matches stamped test images: TC01 → "Photo, 01 January, 12:00 PM", etc.
PHOTO_PICKER_CELL_TEMPLATE: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_CLASS_CHAIN,
    '**/XCUIElementTypeImage[`label == "{TIME_LABEL}"`]',
)
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None

# Preview sheet after picker (FoodZilla-specific if present).
PHOTO_CONFIRM_BUTTON: Optional[Tuple[str, str]] = None

# --- Optional: split detection vs classification labels ---
RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None
