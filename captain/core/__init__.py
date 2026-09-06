"""Core infrastructure for CAPTAIN.

Provides foundational services used across the platform:

- **config** — Centralized configuration via pydantic-settings.
- **exceptions** — Base exception hierarchy.
- **logging** — Standardized application logging.

Sub-modules are imported on demand; this package ``__init__`` does not
eagerly import them.
"""
