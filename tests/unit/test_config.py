"""Tests for CAPTAIN configuration system."""

from pathlib import Path

import pytest

from captain.core.config import CaptainSettings, get_settings


class TestCaptainSettings:
    """Tests for the CaptainSettings configuration class."""

    def test_default_settings_instantiate(self) -> None:
        """Default settings should instantiate without errors."""
        settings = CaptainSettings()
        assert settings.app_name == "CAPTAIN"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.debug is False

    def test_data_dir_is_path(self) -> None:
        """Data directory should be a pathlib.Path."""
        settings = CaptainSettings()
        assert isinstance(settings.data_dir, Path)

    def test_artifacts_dir_is_path(self) -> None:
        """Artifacts directory should be a pathlib.Path."""
        settings = CaptainSettings()
        assert isinstance(settings.artifacts_dir, Path)

    def test_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables with CAPTAIN_ prefix should override defaults."""
        monkeypatch.setenv("CAPTAIN_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("CAPTAIN_DEBUG", "true")
        monkeypatch.setenv("CAPTAIN_ENVIRONMENT", "production")
        settings = CaptainSettings()
        assert settings.log_level == "DEBUG"
        assert settings.debug is True
        assert settings.environment == "production"

    def test_data_dir_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Data directory can be overridden via environment variable."""
        monkeypatch.setenv("CAPTAIN_DATA_DIR", "custom/data/path")
        settings = CaptainSettings()
        assert settings.data_dir == Path("custom/data/path")

    def test_get_settings_returns_instance(self) -> None:
        """get_settings() should return a CaptainSettings instance."""
        settings = get_settings()
        assert isinstance(settings, CaptainSettings)
