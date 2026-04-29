"""FoodZilla page object — placeholder flows only."""

from __future__ import annotations

from pathlib import Path

from appium.webdriver.webdriver import WebDriver

from apps.foodzilla import locators as loc
from framework.base_driver import safe_wait_until_visible
from framework.logger import get_logger

logger = get_logger(__name__)


class FoodzillaPage:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def open_app(self) -> None:
        logger.info("FoodZilla: open_app (session targets bundle_id from config)")

    def tap_scan_or_upload(self) -> None:
        # TODO: Tap the real scan / upload entry point once locators exist.
        logger.info("FoodZilla: tap_scan_or_upload — placeholder")
        el = safe_wait_until_visible(self.driver, loc.PLACEHOLDER_BUTTON, timeout=3)
        if el:
            el.click()

    def select_image(self, image_path: str) -> None:
        # TODO: Drive photo picker / file provider for image_path.
        logger.info("FoodZilla: select_image(%s) — placeholder", image_path)
        _ = Path(image_path)

    def read_result_text(self) -> str:
        # TODO: Read on-screen labels for Food Detection + Food Classification.
        logger.info("FoodZilla: read_result_text — placeholder")
        el = safe_wait_until_visible(self.driver, loc.PLACEHOLDER_RESULT, timeout=3)
        if el and el.text:
            return el.text.strip()
        return ""

    def read_model_output(self) -> str:
        """
        Single string compared to CSV `expected_output` (Deliverable 2B combined output).
        TODO: Format consistently with your 2B spec (e.g. JSON line, or 'detection | classification').
        """
        return self.read_result_text()
