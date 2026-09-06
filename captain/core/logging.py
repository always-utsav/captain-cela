"""Logging configuration for the CAPTAIN project.

Provides a centralized logging setup using Python's standard logging package.
Library modules should use ``get_logger(__name__)`` to obtain a child logger
under the ``captain`` namespace rather than configuring logging themselves.

This module is distinct from CAPTAIN's future execution trace system.
Application logging and execution tracing are separate concerns.
"""

from __future__ import annotations

import logging as _logging
import sys

_DEFAULT_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

_configured: bool = False


def configure_logging(
    level: str = "INFO",
    log_format: str | None = None,
) -> None:
    """Configure the root CAPTAIN logger.

    Sets up a :class:`logging.StreamHandler` on the ``captain`` logger with
    the specified level and format.  Repeated calls update the log level but
    do **not** add duplicate handlers.

    Args:
        level: Logging level name (e.g. ``"INFO"``, ``"DEBUG"``).
        log_format: Optional format string.  Defaults to a pipe-delimited
            format including timestamp, logger name, level, and message.
    """
    global _configured

    logger = _logging.getLogger("captain")
    logger.setLevel(level)

    # Only add a handler on the very first configuration call.
    if not logger.handlers:
        handler = _logging.StreamHandler(sys.stderr)
        fmt = log_format if log_format is not None else _DEFAULT_FORMAT
        handler.setFormatter(_logging.Formatter(fmt))
        logger.addHandler(handler)

    _configured = True


def get_logger(name: str) -> _logging.Logger:
    """Return a child logger under the ``captain`` namespace.

    If logging has not yet been configured, :func:`configure_logging` is
    called with default settings to ensure at least basic logging is active.

    Args:
        name: Dot-separated child logger name (e.g. ``"core.config"``).

    Returns:
        A :class:`logging.Logger` instance named ``captain.<name>``.
    """
    if not _configured:
        configure_logging()

    return _logging.getLogger(f"captain.{name}")
