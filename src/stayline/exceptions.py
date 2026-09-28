"""
src/stayline/exceptions.py
---------------------------
Custom exceptions for the Stayline pipeline.
"""


class StaylineError(Exception):
    """Base class for all Stayline errors."""


class DataValidationError(StaylineError):
    """Raised when the raw or cleaned data fails schema/quality checks."""


class ArtifactMissingError(StaylineError):
    """Raised when a required pipeline artifact (model, DB, CSV) is not found."""


class ConfigError(StaylineError):
    """Raised when a required configuration value is missing or invalid."""
