"""Configuration management for the CAPTAIN project.

Provides a centralized settings object backed by environment variables
(with the ``CAPTAIN_`` prefix) and an optional ``.env`` file.  Settings
are powered by `pydantic-settings <https://docs.pydantic.dev/latest/>`_.

Usage::

    from captain.core.config import get_settings

    settings = get_settings()
    print(settings.log_level)

Configuration values can be overridden by setting environment variables::

    export CAPTAIN_LOG_LEVEL=DEBUG
    export CAPTAIN_DATA_DIR=/mnt/data/captain
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class CaptainSettings(BaseSettings):
    """Central configuration for the CAPTAIN platform.

    All fields can be overridden via environment variables prefixed with
    ``CAPTAIN_`` (e.g. ``CAPTAIN_LOG_LEVEL=DEBUG``).  A ``.env`` file in the
    working directory is also loaded when present.

    Attributes:
        app_name: Human-readable application name.
        environment: Deployment environment (``development``, ``staging``,
            ``production``).
        log_level: Python logging level name.
        data_dir: Root directory for data storage.
        artifacts_dir: Directory for generated artifacts.
        debug: Enable verbose debug behaviour.
    """

    model_config = SettingsConfigDict(
        env_prefix="CAPTAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CAPTAIN"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    artifacts_dir: Path = Path("data/artifacts")
    debug: bool = False


def get_settings() -> CaptainSettings:
    """Create and return a fresh :class:`CaptainSettings` instance.

    Each call reads the current environment, so callers always receive
    up-to-date values.  The function intentionally does **not** cache a
    singleton to avoid hidden side-effects at import time.

    Returns:
        A fully-resolved :class:`CaptainSettings` object.
    """
    return CaptainSettings()
