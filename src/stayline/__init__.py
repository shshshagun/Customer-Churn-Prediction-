"""
Stayline Retention Intelligence
================================
src/stayline/__init__.py

Public package marker.  Import the package-level logger so callers can do:
    import stayline; stayline.logger.info(...)
"""

from stayline.logging_setup import get_logger

logger = get_logger(__name__)

__version__ = "1.0.0"
__all__ = ["logger"]
