"""
src/stayline/logging_setup.py
------------------------------
Centralised logging configuration.

Usage:
    from stayline.logging_setup import get_logger
    logger = get_logger(__name__)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger that writes to both stderr and logs/pipeline.log."""
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — avoid duplicate handlers
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler — create logs/ lazily
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
