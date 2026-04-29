# TODO: Replace placeholder accessibility IDs / predicates with real locators from
# your FoodZilla build (inspect via Appium Inspector / Xcode).

# Example patterns — do not use until verified on device:
# SCAN_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "scan")
# RESULT_LABEL = (AppiumBy.IOS_PREDICATE, 'label == "detection_result"')

from appium.webdriver.common.appiumby import AppiumBy

# Placeholder locators — must be updated before real runs succeed.
PLACEHOLDER_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_SCAN_BUTTON")
PLACEHOLDER_RESULT = (AppiumBy.ACCESSIBILITY_ID, "TODO_FOODZILLA_RESULT_TEXT")
