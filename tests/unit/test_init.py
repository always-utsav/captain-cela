"""Tests for CAPTAIN package initialization."""

import captain


class TestPackageInit:
    """Tests for the captain package metadata."""

    def test_version_exists(self) -> None:
        """Package should expose __version__."""
        assert hasattr(captain, "__version__")

    def test_version_is_string(self) -> None:
        """__version__ should be a string."""
        assert isinstance(captain.__version__, str)

    def test_version_format(self) -> None:
        """__version__ should follow semver-like format."""
        parts = captain.__version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()
