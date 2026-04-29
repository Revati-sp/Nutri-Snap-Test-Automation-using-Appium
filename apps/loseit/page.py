"""Lose It! page object — placeholder flows only."""

from __future__ import annotations

from pathlib import Path

from appium.webdriver.webdriver import WebDriver

from apps.loseit import locators as loc
from framework.base_driver import safe_wait_until_visible
from framework.logger import get_logger

logger = get_logger(__name__)


class LoseItPage:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def open_app(self) -> None:
        logger.info("Lose It!: open_app (session targets bundle_id from config)")

    def tap_scan_or_upload(self) -> None:
        logger.info("Lose It!: tap_scan_or_upload — placeholder")
        el = safe_wait_until_visible(self.driver, loc.PLACEHOLDER_BUTTON, timeout=3)
        if el:
            el.click()

    def select_image(self, image_path: str) -> None:
        logger.info("Lose It!: select_image(%s) — placeholder", image_path)
        _ = Path(image_path)

    def read_result_text(self) -> str:
        logger.info("Lose It!: read_result_text — placeholder")
        el = safe_wait_until_visible(self.driver, loc.PLACEHOLDER_RESULT, timeout=3)
        if el and el.text:
            return el.text.strip()
        return ""

    def read_model_output(self) -> str:
        """TODO: Align format with Deliverable 2B `expected_output` for this app."""
        return self.read_result_text()
