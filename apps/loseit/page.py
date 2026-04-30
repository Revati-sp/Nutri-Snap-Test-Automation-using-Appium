"""Lose It! page object — scan → image → read (locators drive real UI)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from appium.webdriver.webdriver import WebDriver

from apps.loseit import locators as loc
from framework.ios_food_scan_page import IosFoodScanPageBase


class LoseItPage(IosFoodScanPageBase):
    def __init__(self, driver: WebDriver, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(driver, config, loc, "Lose It!")
