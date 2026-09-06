"""Tests for CAPTAIN logging infrastructure."""

import logging

from captain.core.logging import configure_logging, get_logger


class TestLogging:
    """Tests for the logging configuration system."""

    def test_get_logger_returns_logger(self) -> None:
        """get_logger should return a logging.Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_uses_captain_namespace(self) -> None:
        """Loggers should be in the 'captain' namespace."""
        logger = get_logger("mymodule")
        assert logger.name == "captain.mymodule"

    def test_configure_logging_sets_level(self) -> None:
        """configure_logging should set the specified log level."""
        configure_logging(level="DEBUG")
        root_logger = logging.getLogger("captain")
        assert root_logger.level == logging.DEBUG
        # Reset
        configure_logging(level="INFO")

    def test_no_duplicate_handlers(self) -> None:
        """Repeated calls to configure_logging should not create duplicate handlers."""
        configure_logging(level="INFO")
        root_logger = logging.getLogger("captain")
        handler_count = len(root_logger.handlers)
        configure_logging(level="INFO")
        assert len(root_logger.handlers) == handler_count
