"""SnapCalorie page object."""
from __future__ import annotations
from typing import Any, Mapping, Optional
from appium.webdriver.webdriver import WebDriver
from apps.snapcalorie import locators as loc
from framework.ios_food_scan_page import IosFoodScanPageBase
from framework.base_driver import safe_wait_until_visible
from appium.webdriver.common.appiumby import AppiumBy
import time
import re

class SnapcaloriePage(IosFoodScanPageBase):
    def __init__(self, driver: WebDriver, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(driver, config, loc, "SnapCalorie")

    def _mobile_tap(self, x: int, y: int) -> None:
        self.driver.execute_script('mobile: tap', {'x': x, 'y': y})

    def _dismiss_popup(self) -> bool:
        els = self.driver.find_elements(AppiumBy.XPATH, '//*[@name]')
        for el in els:
            name = el.get_attribute('name') or ''
            if 'Upgrade' in name or 'trial' in name.lower() or 'Upgrading' in name:
                self._mobile_tap(62, 208)
                time.sleep(2)
                return True
        return False

    def tap_scan_or_upload(self) -> None:
        time.sleep(8)
        self._mobile_tap(201, 787)
        time.sleep(4)
        self._dismiss_popup()

        food_els = self.driver.find_elements(
            AppiumBy.XPATH, '//*[contains(@name, "Food")]'
        )
        if food_els:
            food_els[0].click()
        else:
            self._mobile_tap(120, 710)
        time.sleep(4)
        self._dismiss_popup()

        self._mobile_tap(35, 675)
        time.sleep(4)

    # Track which image we're on
    _image_counter = 0

    def select_image(self, image_path: str) -> None:
        # Use sequential counter - phone has images in order
        idx = SnapcaloriePage._image_counter
        SnapcaloriePage._image_counter += 1

        col = idx % 3
        row = idx // 3
        x = 67 + col * 134
        y = 217 + row * 134
        self._mobile_tap(x, y)
        time.sleep(3)

        done_btns = self.driver.find_elements(
            AppiumBy.XPATH, '//XCUIElementTypeButton[@name="Done"]'
        )
        if done_btns:
            done_btns[0].click()
        else:
            self._mobile_tap(355, 800)
        time.sleep(4)

        all_els = self.driver.find_elements(AppiumBy.XPATH, '//*[@name]')
        for el in all_els:
            name = el.get_attribute('name') or ''
            if 'Save' in name:
                eloc = el.location
                size = el.size
                cx = eloc['x'] + size['width'] // 2
                cy = eloc['y'] + size['height'] // 2
                self._mobile_tap(cx, cy)
                break
        else:
            self._mobile_tap(201, 810)
        time.sleep(3)
        self._dismiss_popup()
        time.sleep(5)

    def read_model_output(self) -> str:
        time.sleep(8)
        el = safe_wait_until_visible(
            self.driver,
            (AppiumBy.XPATH, '//XCUIElementTypeStaticText[contains(@name, "calories,")]'),
            timeout=30.0
        )
        if el and el.text:
            return el.text.strip()
        el2 = safe_wait_until_visible(
            self.driver,
            (AppiumBy.XPATH, '//XCUIElementTypeOther[contains(@name, "calories")]'),
            timeout=10.0
        )
        if el2:
            return el2.get_attribute('name') or ''
        return ''
