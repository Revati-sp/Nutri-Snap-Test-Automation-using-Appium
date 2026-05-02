# Replace TODO values using Appium Inspector / Xcode for Lose It!.

from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

# Step 1 — opens the Breakfast meal options sheet.
SCAN_ENTRY = (AppiumBy.ACCESSIBILITY_ID, "Meal options menu for Breakfast")

# Step 2 — the option in the action sheet that launches the photo scanner.
SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = (AppiumBy.ACCESSIBILITY_ID, "Snap It")

# Step 3 — iOS PHPicker navigation.
# Lose It!'s camera screen has a green gallery icon (SF Symbol: photo.circle)
# at the bottom-left that opens the iOS PHPicker.
PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = (AppiumBy.ACCESSIBILITY_ID, "photo.circle")

# PHPicker remembers the last tab; force "Collections" so we can navigate to NutriSnapTests album.
PHOTO_PICKER_COLLECTIONS_TAB: Optional[Tuple[str, str]] = (AppiumBy.ACCESSIBILITY_ID, "Collections")

# Album buttons in PHPicker have unstable `name` (ObjectIdentifier(0x...)) but stable `label`.
# Use an iOS predicate string to target by label.
PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "NutriSnapTests"',
)
# Inside NutriSnapTests, every thumbnail is `XCUIElementTypeImage[name=="PXGGridLayout-Info"]`,
# and crucially each cell carries a stable VoiceOver label derived from the photo's EXIF capture
# time, e.g. "Photo, 01 January, 12:00 PM". `scripts/stamp_test_images.py` writes progressive
# DateTimeOriginal stamps starting at 2026-01-01 12:00 PM with +10-minute increments per TC,
# so {TIME_LABEL} is filled in by the framework as:
#     TC01 -> "Photo, 01 January, 12:00 PM"
#     TC02 -> "Photo, 01 January, 12:10 PM"
#     ...
#     TC07 -> "Photo, 01 January, 1:00 PM"   (rolls hour at 6, 12, 18, 24, 30 cells)
# This is far more stable than ordinal indexing, which breaks if the picker scrolls or filters.
PHOTO_PICKER_CELL_TEMPLATE: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_CLASS_CHAIN,
    '**/XCUIElementTypeImage[`label == "{TIME_LABEL}"`]',
)
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None  # static fallback; template above takes precedence

# Step 3.5 — Lose It! shows a "Choose Photo" preview after the picker; tap "Choose" to confirm.
# Native Lose It! button (`name="Done"` with `label="Choose"`).
PHOTO_CONFIRM_BUTTON: Optional[Tuple[str, str]] = (AppiumBy.ACCESSIBILITY_ID, "Done")

# Step 4 — Lose It!'s "Smart Logging Triage" result screen.
# It shows multiple candidates; the top one is the first StaticText with format "<Category>, <Name>"
# (e.g. "Juice, Pomegranate"). The serving info ("X cals per Y") and section header ("Breakfast: N cals")
# are excluded.
RESULT_PANEL = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeStaticText" AND name CONTAINS ", " '
    'AND NOT (name BEGINSWITH "Breakfast" OR name BEGINSWITH "Lunch" '
    'OR name BEGINSWITH "Dinner" OR name BEGINSWITH "Snacks" '
    'OR name CONTAINS "cals" OR name CONTAINS "Premium" OR name CONTAINS "complimentary")',
)
RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None

PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL
