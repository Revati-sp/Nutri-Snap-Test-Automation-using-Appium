"""SnapCalorie test execution hooks."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from appium.webdriver.webdriver import WebDriver

from apps.snapcalorie.page import SnapcaloriePage
from framework.logger import get_logger

logger = get_logger(__name__)


def run_single_test(
    driver: WebDriver,
    testcase: dict[str, str],
    config: dict[str, Any],
) -> Tuple[str, Optional[str]]:
    page = SnapcaloriePage(driver, config)
    try:
        page.open_app()
        page.tap_scan_or_upload()
        image = testcase.get("image_path", "")
        if image:
            page.select_image(image)
        return page.read_model_output(), None
    except Exception as exc:  # noqa: BLE001
        logger.exception("SnapCalorie test execution error")
        return "", str(exc)
