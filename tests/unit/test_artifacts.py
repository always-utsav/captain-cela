"""Tests for captain.models.artifacts -- Artifact canonical model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType
from captain.models.ids import generate_artifact_id, generate_event_id


class TestArtifact:
    """Tests for the Artifact model."""

    def test_construction_with_text(self) -> None:
        art = Artifact(artifact_type=ArtifactType.TEXT, value="hello")
        assert art.artifact_id.startswith("art_")
        assert art.artifact_type == ArtifactType.TEXT
        assert art.value == "hello"
        assert art.reference is None

    def test_construction_with_reference(self) -> None:
        art = Artifact(artifact_type=ArtifactType.IMAGE, reference="s3://bucket/img.png")
        assert art.reference == "s3://bucket/img.png"
        assert art.value is None

    def test_construction_with_structured_data(self) -> None:
        data = {"key": "value", "nested": [1, 2, 3]}
        art = Artifact(artifact_type=ArtifactType.STRUCTURED_DATA, value=data)
        assert art.value == data

    def test_producer_event_id(self) -> None:
        eid = generate_event_id()
        art = Artifact(
            artifact_type=ArtifactType.TOOL_OUTPUT, value="result", producer_event_id=eid
        )
        assert art.producer_event_id == eid

    def test_metadata(self) -> None:
        art = Artifact(
            artifact_type=ArtifactType.TEXT,
            value="x",
            metadata={"source": "planner"},
        )
        assert art.metadata["source"] == "planner"

    def test_created_at_is_utc(self) -> None:
        art = Artifact(artifact_type=ArtifactType.TEXT, value="x")
        assert art.created_at.tzinfo is not None

    def test_explicit_id(self) -> None:
        aid = generate_artifact_id()
        art = Artifact(artifact_id=aid, artifact_type=ArtifactType.TEXT, value="x")
        assert art.artifact_id == aid

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Artifact(artifact_id="", artifact_type=ArtifactType.TEXT, value="x")

    def test_wrong_id_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="start with 'art_'"):
            Artifact(artifact_id="evt_123", artifact_type=ArtifactType.TEXT, value="x")

    def test_explicit_timestamp(self) -> None:
        ts = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        art = Artifact(artifact_type=ArtifactType.TEXT, value="x", created_at=ts)
        assert art.created_at == ts
