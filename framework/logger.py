"""Structured logging setup for the automation framework."""

from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO, name: str = "appium_framework") -> logging.Logger:
    """Configure both the named application logger AND the root logger.

    Module loggers retrieved via ``logging.getLogger(__name__)`` (e.g. ``framework.foo``)
    do NOT inherit from the named logger; without a root-level handler their INFO logs
    are silently dropped. We therefore install a handler on the root logger as well so
    every framework module's INFO+ messages show up on stdout.
    """
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setLevel(level)
        root_handler.setFormatter(fmt)
        root.addHandler(root_handler)
    if root.level == logging.WARNING or root.level == logging.NOTSET:
        root.setLevel(level)

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.propagate = False  # Avoid duplicate emission since root also has a handler.
    logger.setLevel(level)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "appium_framework")
