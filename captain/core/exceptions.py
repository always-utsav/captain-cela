"""Core exception hierarchy for the CAPTAIN project.

All CAPTAIN-specific exceptions inherit from :class:`CaptainError` so that
callers can catch the entire family with a single ``except CaptainError``
clause when appropriate.

Keep this hierarchy minimal.  Add new exception classes only when a concrete
module genuinely needs to distinguish a new failure mode.
"""

from __future__ import annotations


class CaptainError(Exception):
    """Base exception for all CAPTAIN-specific errors."""


class ConfigurationError(CaptainError):
    """Raised when a configuration value is missing, invalid, or inconsistent."""


class ValidationError(CaptainError):
    """Raised when data fails validation against expected schemas or constraints."""


class StorageError(CaptainError):
    """Raised when a storage or persistence operation fails."""


class AdapterError(CaptainError):
    """Raised when an external-system adapter encounters an error."""
