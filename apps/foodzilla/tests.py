"""FoodZilla test execution hooks — wire real flows in page.py first."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from appium.webdriver.webdriver import WebDriver

from apps.foodzilla.page import FoodzillaPage
from framework.logger import get_logger

logger = get_logger(__name__)


def run_single_test(
    driver: WebDriver,
    testcase: dict[str, str],
    config: dict[str, Any],
) -> Tuple[str, Optional[str]]:
    """
    Execute one CSV/JSON row for FoodZilla.
    Returns (actual_output, error_message) where actual_output matches Deliverable 2B combined output.
    """
    page = FoodzillaPage(driver, config)
    try:
        page.open_app()
        page.tap_scan_or_upload()
        image = testcase.get("image_path", "")
        if image:
            page.select_image(image)
        return page.read_model_output(), None
    except Exception as exc:  # noqa: BLE001
        logger.exception("FoodZilla test execution error")
        return "", str(exc)
