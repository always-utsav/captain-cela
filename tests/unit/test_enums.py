"""Tests for captain.models.enums -- canonical enumerations."""

from __future__ import annotations

from captain.models.enums import ArtifactType, EventType, RunStatus


class TestEventType:
    """Tests for the EventType enum."""

    def test_all_required_members_exist(self) -> None:
        required = [
            "INPUT",
            "PLANNING",
            "REASONING",
            "MEMORY_READ",
            "MEMORY_WRITE",
            "TOOL_CALL",
            "TOOL_RESULT",
            "MODEL_CALL",
            "MODEL_RESULT",
            "OUTPUT",
            "ERROR",
        ]
        for name in required:
            assert hasattr(EventType, name), f"EventType.{name} missing"

    def test_values_are_lowercase_strings(self) -> None:
        for member in EventType:
            assert member.value == member.value.lower()
            assert isinstance(member.value, str)

    def test_str_serialization(self) -> None:
        assert str(EventType.TOOL_CALL) == "tool_call"


class TestRunStatus:
    """Tests for the RunStatus enum."""

    def test_all_required_members_exist(self) -> None:
        for name in ["CREATED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]:
            assert hasattr(RunStatus, name)

    def test_str_serialization(self) -> None:
        assert str(RunStatus.CREATED) == "created"
        assert str(RunStatus.COMPLETED) == "completed"


class TestArtifactType:
    """Tests for the ArtifactType enum."""

    def test_all_required_members_exist(self) -> None:
        for name in ["TEXT", "IMAGE", "STRUCTURED_DATA", "FILE", "TOOL_OUTPUT", "MODEL_OUTPUT"]:
            assert hasattr(ArtifactType, name)

    def test_str_serialization(self) -> None:
        assert str(ArtifactType.TEXT) == "text"
        assert str(ArtifactType.STRUCTURED_DATA) == "structured_data"
