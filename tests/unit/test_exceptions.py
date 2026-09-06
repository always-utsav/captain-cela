"""Tests for CAPTAIN exception hierarchy."""

import pytest

from captain.core.exceptions import (
    AdapterError,
    CaptainError,
    ConfigurationError,
    StorageError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Tests for the custom exception hierarchy."""

    def test_captain_error_is_exception(self) -> None:
        """CaptainError should inherit from Exception."""
        assert issubclass(CaptainError, Exception)

    def test_configuration_error_inherits_captain(self) -> None:
        """ConfigurationError should inherit from CaptainError."""
        assert issubclass(ConfigurationError, CaptainError)

    def test_validation_error_inherits_captain(self) -> None:
        """ValidationError should inherit from CaptainError."""
        assert issubclass(ValidationError, CaptainError)

    def test_storage_error_inherits_captain(self) -> None:
        """StorageError should inherit from CaptainError."""
        assert issubclass(StorageError, CaptainError)

    def test_adapter_error_inherits_captain(self) -> None:
        """AdapterError should inherit from CaptainError."""
        assert issubclass(AdapterError, CaptainError)

    def test_captain_error_can_be_raised_with_message(self) -> None:
        """CaptainError should accept and preserve a message."""
        error = CaptainError("test message")
        assert str(error) == "test message"

    def test_catch_captain_error_catches_subtypes(self) -> None:
        """Catching CaptainError should catch all subtypes."""
        with pytest.raises(CaptainError):
            raise ConfigurationError("bad config")

        with pytest.raises(CaptainError):
            raise ValidationError("bad data")

        with pytest.raises(CaptainError):
            raise StorageError("disk full")

        with pytest.raises(CaptainError):
            raise AdapterError("adapter failed")
