# FoodZilla — map app-specific controls via Appium Inspector / Xcode on YOUR build.
#
# Framework contract (`framework/ios_food_scan_page.py`):
#   Required: SCAN_ENTRY, RESULT_PANEL (or legacy PLACEHOLDER_* aliases).
#   Optional: SCAN_FALLBACK_LOCATORS, SCAN_SECONDARY_TAP, full PHPicker chain,
#             PHOTO_CONFIRM_BUTTON, RESULT_DETECTION + RESULT_CLASSIFICATION (split labels).
#   Result tuning (when CSV-guided fallback scans labels):
#             RESULT_SCAN_EXCLUDE_SUBSTRINGS — lowercase substrings to skip (toolbar/noise).
#             RESULT_FALLBACK_SCAN_EXTRA_PREDICATES — extra `-ios predicate string` queries (e.g. Other).
#             RESULT_FALLBACK_SCAN_PREDICATES — if set, replaces the default StaticText+Button scan list.
#
# Shared test assets use album "NutriSnapTests" and EXIF-based picker labels;
# see `scripts/stamp_test_images.py` and PHOTO_PICKER_CELL_TEMPLATE below.

from typing import Dict, List, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

# --- Home (Food Intake diary): top-right camera icon ---
# Inspector page source: three toolbar glyphs are XCUIElementTypeOther; camera is the rightmost,
# frame ~38x41 (plus/search are ~40x41 and ~39x41). name/label are SF Symbol private-use chars,
# so we avoid brittle Unicode and match geometry + header Y band.
SCAN_ENTRY = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeOther" AND accessible == true '
    'AND width == 38 AND height == 41 AND y >= 62 AND y <= 120',
)

# Tap toolbar camera when predicates fail. Tune using Inspector “Box Model” on YOUR phone width.
# If tapping opens search/notifications, nudge X/Y or reorder SCAN_COORDINATE_ALTERNATES.
SCAN_COORDINATE_FALLBACK: Tuple[int, int] = (400, 112)
# Extra taps tried if primary coordinate misses (Dynamic Island / different widths).
SCAN_COORDINATE_ALTERNATES: Tuple[Tuple[int, int], ...] = (
    (382, 112),
    (418, 112),
    (400, 102),
)

# When SCAN_ENTRY misses (Dynamic Type, layout, or OS changes), try text/icons then geometry again.
SCAN_FALLBACK_LOCATORS: list[Tuple[str, str]] = [
    (AppiumBy.IOS_PREDICATE, 'label == "Camera"'),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Take Photo"'),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Log food"'),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Add food"'),
    (
        AppiumBy.IOS_PREDICATE,
        '(type == "XCUIElementTypeButton" OR type == "XCUIElementTypeStaticText") '
        'AND (label CONTAINS[c] "scan" OR label CONTAINS[c] "camera" OR label CONTAINS[c] "snap" '
        'OR label CONTAINS[c] "photo" OR label CONTAINS[c] "gallery")',
    ),
    (
        AppiumBy.IOS_PREDICATE,
        'type == "XCUIElementTypeButton" AND label CONTAINS[c] "food"',
    ),
    (
        AppiumBy.IOS_PREDICATE,
        'type == "XCUIElementTypeTabBarButton" AND (label CONTAINS[c] "scan" OR label CONTAINS[c] "home")',
    ),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "From Gallery"'),
]

# After CV analysis: `read_model_output()` reads display text (text/label/name/value) and compares to
# CSV `expected_output`. Widen ORs for common foods; add RESULT_PANEL_FALLBACKS if the title is not
# StaticText. If the app uses different strings, use Appium Inspector and add a predicate or
# RESULT_PANEL_CANDIDATES (full ordered list) in this file.
RESULT_PANEL = (
    AppiumBy.IOS_PREDICATE,
    '(type == "XCUIElementTypeStaticText" OR type == "XCUIElementTypeButton") AND ('
    'label CONTAINS[c] "Pomegranate" OR name CONTAINS[c] "Pomegranate" OR '
    'label CONTAINS[c] "Popcorn" OR name CONTAINS[c] "Popcorn" OR '
    'label CONTAINS[c] "Pasta" OR name CONTAINS[c] "Pasta" OR '
    'label CONTAINS[c] "Spaghetti" OR name CONTAINS[c] "Spaghetti" OR '
    'label CONTAINS[c] "Egg" OR name CONTAINS[c] "Egg" OR '
    'label CONTAINS[c] "Madelein" OR name CONTAINS[c] "Madelein"'
    ')',
)
# Tried if primary matches nothing or matched node has no readable text.
RESULT_PANEL_FALLBACKS: List[Tuple[str, str]] = [
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Pomegranate"'),
    (AppiumBy.IOS_PREDICATE, 'name CONTAINS[c] "Pomegranate"'),
    (AppiumBy.IOS_PREDICATE, 'value CONTAINS[c] "Pomegranate"'),
    # Avoid label CONTAINS "Apple" (matches Pineapple); use exact / juice-style titles if needed.
    (AppiumBy.IOS_PREDICATE, 'label == "Apple" OR name == "Apple"'),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Egg"'),
    (AppiumBy.IOS_PREDICATE, 'label CONTAINS[c] "Madelein"'),
]

# Labels containing these normalized substrings are ignored during CSV-guided fallback scanning.
# Add/remove strings after you inspect `reports/debug/result_read_empty_*.xml` (see scripts below).
RESULT_SCAN_EXCLUDE_SUBSTRINGS: Sequence[str] = (
    "cancel",
    "done",
    "close",
    "back",
    "sort and filter",
    "choose photos",
    "browse",
)

# SwiftUI / custom stacks sometimes expose readable titles on XCUIElementTypeOther instead of StaticText.
RESULT_FALLBACK_SCAN_EXTRA_PREDICATES: Sequence[str] = (
    'type == "XCUIElementTypeOther" AND accessible == true',
)

PLACEHOLDER_BUTTON = SCAN_ENTRY
PLACEHOLDER_RESULT = RESULT_PANEL

SCAN_SECONDARY_TAP: Optional[Tuple[str, str]] = None

# --- Scan Meal screen (second page after home camera) ---
# Page source: title "Scan Meal", toolbar glyphs use SF Symbols (private-use name/label).
# Bottom-left gallery control: XCUIElementTypeOther with name/label like "*prefix*, From Gallery";
# match on substring so we do not embed the icon character.
SCAN_MEAL_TITLE: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeStaticText" AND label == "Scan Meal"',
)
SCAN_MEAL_SUBTITLE: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label == "Capture your meal"',
)
POSITION_FOOD_HERE_HINT: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label == "Position food here"',
)
SCAN_ANY_FOOD_BANNER: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label == "Scan Any Food in Seconds"',
)
SCAN_BARCODE_BUTTON: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label CONTAINS[c] "Scan Barcode"',
)

# --- Bridge into iOS PHPicker (in-app "From Gallery" on Scan Meal, then system picker) ---
# Prefer FoodZilla's Scan Meal control first; fall through to stock Photo Library strings.
PHOTO_LIBRARY_BUTTON: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    '(label CONTAINS[c] "From Gallery") OR (label == "Photo Library") OR (label == "Choose Photos") '
    'OR (label CONTAINS[c] "photo library") OR (label == "Browse") OR (label CONTAINS[c] "album")',
)

# --- Photos picker sheet (third page: tap From Gallery → embedded Photos UI) ---
# XML: NavigationBar Cancel; segmented Photos | Collections; scroll grid of XCUIElementTypeImage
# name="PXGGridLayout-Info" with VoiceOver labels like "Photo, May 01, 9:22 PM"; toolbar Sort and Filter / Search.
PHOTO_PICKER_CANCEL_BUTTON: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "Cancel"',
)
PHOTO_PICKER_PHOTOS_SEGMENT: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "Photos"',
)
PHOTOS_TOOLBAR_SORT_FILTER: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "Sort and Filter"',
)
PHOTOS_TOOLBAR_SEARCH: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "Search"',
)
# First matching grid cell — many thumbnails share name PXGGridLayout-Info; prefer PHOTO_PICKER_CELL_TEMPLATE + TIME_LABEL when stamped assets are used.
PHOTO_GRID_CELL_FALLBACK: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_CLASS_CHAIN,
    '**/XCUIElementTypeImage[`name == "PXGGridLayout-Info"`]',
)

# --- Picker navigation: Photos grid only (no Collections / album) ---
# Leave Collections + album unset so automation picks tiles from the main “Photos” tab Recents grid.
# PHOTO_PICKER_PHOTOS_SEGMENT is tapped after “From Gallery” so a remembered Collections tab switches back.
PHOTO_PICKER_COLLECTIONS_TAB: Optional[Tuple[str, str]] = None
PHOTO_ALBUM_ROW: Optional[Tuple[str, str]] = None

# Matches stamped test images: TC01 → "Photo, 01 January, 12:00 PM", etc. (see scripts/stamp_test_images.py).
PHOTO_PICKER_CELL_TEMPLATE: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_CLASS_CHAIN,
    '**/XCUIElementTypeImage[`label == "{TIME_LABEL}"`]',
)
PHOTO_PICKER_CELL: Optional[Tuple[str, str]] = None

# Recents grid (Photos tab, YOUR phone screenshot — slot = left→right, top→bottom):
#   1 pasta/spaghetti | 2 popcorn plush | 3 madeleines
#   4 apple           | 5 pomegranate juice | 6 meal-app screenshot
# CSV mapping / picker tap uses TC## from image filename: TC01 pomegranate→5, TC02 pasta→1, TC03 apple→4,
# TC16 madeleines→3, TC32 popcorn plush→2, TC04 eggs→(not in slots 1–6).
# Note: slot 4 is Apple (TC03), not TC04 — TC04 expects Eggs per testcases.csv; eggs must appear as tile 7+ or scroll first.
PHOTO_GRID_TAP_OVERRIDE: Dict[int, Tuple[int, int]] = {
    1: (221, 374),  # TC01 pomegranate slot 5 row2 col2
    2: (74, 227),  # TC02 pasta slot 1 row1 col1
    3: (74, 374),  # TC03 apple slot 4 row2 col1
    # TC04 eggs: tiles 1–6 have no eggs. Default = slot 7 (row 3 col 1); if eggs is under pomegranate same column → (221, 521).
    4: (74, 521),
    16: (368, 227),  # TC16 Madeleins — slot 3 top-right (same column as meal screenshot below)
    32: (221, 227),  # TC32 popcorn plush — slot 2 row1 col2 (needs data/images/TC32.jpg + testcases row 32)
}

PHOTO_CONFIRM_BUTTON: Optional[Tuple[str, str]] = None

# --- Meal preview / “final” screen (detected food before saving to diary) — optional unless you tap them ---
ADD_TO_DIARY_BUTTON: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'type == "XCUIElementTypeButton" AND label == "Add to Diary"',
)
ADD_FOODS_BUTTON: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label == "Add Foods"',
)
NUTRITION_DETAILS_LINK: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label == "Nutrition Details"',
)
MEAL_TYPE_SNACK_HEADER: Optional[Tuple[str, str]] = (
    AppiumBy.IOS_PREDICATE,
    'label CONTAINS[c] "Snack"',
)

RESULT_DETECTION: Optional[Tuple[str, str]] = None
RESULT_CLASSIFICATION: Optional[Tuple[str, str]] = None
