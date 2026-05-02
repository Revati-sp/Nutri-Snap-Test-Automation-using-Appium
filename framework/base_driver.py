"""Appium WebDriver factory and explicit-wait helpers for iOS (XCUITest)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.config_loader import get_nested
from framework.logger import get_logger

logger = get_logger(__name__)


def build_xcuitest_options(config: dict[str, Any]) -> XCUITestOptions:
    """Build XCUITestOptions from normalized YAML config (no app-specific logic)."""
    opts = XCUITestOptions()
    opts.platform_name = "iOS"
    opts.device_name = str(get_nested(config, "device", "name", default="iPhone") or "iPhone")
    udid = get_nested(config, "device", "udid", default="")
    if udid:
        opts.udid = str(udid)
    pv = get_nested(config, "device", "platform_version", default="")
    if pv:
        opts.platform_version = str(pv)
    bundle = get_nested(config, "app", "bundle_id", default="")
    if bundle:
        opts.bundle_id = str(bundle)
    # Override WDA bundle id (free Personal Team can't register the default com.facebook.* id).
    wda_bundle = get_nested(config, "app", "updated_wda_bundle_id", default="")
    if wda_bundle:
        opts.updated_wda_bundle_id = str(wda_bundle)
    org = get_nested(config, "xcode", "org_id", default="")
    if org:
        opts.xcode_org_id = str(org)
    sid = get_nested(config, "xcode", "signing_id", default="")
    if sid:
        opts.xcode_signing_id = str(sid)
    wda_port = get_nested(config, "session", "wda_local_port", default=None)
    if wda_port is not None and str(wda_port).strip():
        opts.wda_local_port = int(wda_port)
    nct = get_nested(config, "session", "new_command_timeout", default=120)
    if nct is not None:
        opts.new_command_timeout = int(nct)
    # Log full xcodebuild output on Appium server (helps WDA failures: signing, license, SDK).
    sx = get_nested(config, "session", "show_xcode_log", default=True)
    opts.show_xcode_log = bool(sx)
    # Passes -allowProvisioningUpdates to xcodebuild so WDA can auto-sign (required for many setups).
    apr = get_nested(config, "session", "allow_provisioning_device_registration", default=True)
    opts.allow_provisioning_device_registration = bool(apr)
    # Increase WDA launch timeout for first install on free Personal Team / large device builds.
    wlt = get_nested(config, "session", "wda_launch_timeout", default=None)
    if wlt is not None and str(wlt).strip():
        opts.wda_launch_timeout = int(wlt)
    wsr = get_nested(config, "session", "wda_startup_retries", default=None)
    if wsr is not None and str(wsr).strip():
        opts.wda_startup_retries = int(wsr)
    opts.automation_name = "XCUITest"
    return opts


def create_ios_driver(config: dict[str, Any]) -> WebDriver:
    url = str(get_nested(config, "appium", "server_url", default="http://127.0.0.1:4723"))
    options = build_xcuitest_options(config)
    logger.info("Starting Appium session at %s", url)
    driver = webdriver.Remote(command_executor=url, options=options)
    return driver


def save_screenshot(driver: WebDriver, path: str | Path) -> Optional[str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        driver.get_screenshot_as_file(str(path))
        logger.info("Screenshot saved: %s", path)
        return str(path)
    except Exception as exc:  # noqa: BLE001 — best effort for diagnostics
        logger.warning("Could not save screenshot: %s", exc)
        return None


def wait_for(
    driver: WebDriver,
    condition: Callable[[WebDriver], Any],
    timeout: float = 20.0,
    poll: float = 0.5,
) -> Any:
    """Explicit wait wrapper."""
    return WebDriverWait(driver, timeout, poll_frequency=poll).until(condition)


def wait_until_visible(driver: WebDriver, locator: tuple[str, str], timeout: float = 20.0) -> Any:
    return wait_for(driver, EC.visibility_of_element_located(locator), timeout=timeout)


def safe_wait_until_visible(
    driver: WebDriver, locator: tuple[str, str], timeout: float = 20.0
) -> Optional[Any]:
    try:
        return wait_until_visible(driver, locator, timeout=timeout)
    except TimeoutException:
        return None


def wait_until_present(driver: WebDriver, locator: tuple[str, str], timeout: float = 20.0) -> Any:
    """Like wait_until_visible but only requires the element to exist in the DOM.

    Needed for iOS PHPicker virtualized grids: cells report ``visible="false"`` even when
    rendered and tappable, so visibility_of_element_located times out unfairly.
    """
    return wait_for(driver, EC.presence_of_element_located(locator), timeout=timeout)


def safe_wait_until_present(
    driver: WebDriver, locator: tuple[str, str], timeout: float = 20.0
) -> Optional[Any]:
    try:
        return wait_until_present(driver, locator, timeout=timeout)
    except TimeoutException:
        return None
