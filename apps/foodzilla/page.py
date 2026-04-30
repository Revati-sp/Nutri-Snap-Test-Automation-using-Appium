"""FoodZilla page object — scan → image → read (locators drive real UI)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from appium.webdriver.webdriver import WebDriver

from apps.foodzilla import locators as loc
from framework.ios_food_scan_page import IosFoodScanPageBase


class FoodzillaPage(IosFoodScanPageBase):
    """Steps: open_app → tap_scan_or_upload → select_image → read_model_output."""

    def __init__(self, driver: WebDriver, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(driver, config, loc, "FoodZilla")
