"""Tests for JSON serialization/deserialization round-trips of canonical models.

Verifies that all canonical models survive:
    model -> JSON dict -> JSON string -> JSON dict -> model
without loss of information.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_event_id, generate_run_id


class TestArtifactSerialization:
    """Round-trip tests for Artifact."""

    def test_text_artifact_round_trip(self) -> None:
        art = Artifact(
            artifact_type=ArtifactType.TEXT,
            value="hello world",
            metadata={"source": "test"},
        )
        json_str = art.model_dump_json()
        restored = Artifact.model_validate_json(json_str)
        assert restored.artifact_id == art.artifact_id
        assert restored.artifact_type == ArtifactType.TEXT
        assert restored.value == "hello world"
        assert restored.metadata == {"source": "test"}

    def test_reference_artifact_round_trip(self) -> None:
        art = Artifact(
            artifact_type=ArtifactType.IMAGE,
            reference="file:///tmp/img.png",
        )
        json_str = art.model_dump_json()
        restored = Artifact.model_validate_json(json_str)
        assert restored.reference == "file:///tmp/img.png"
        assert restored.value is None

    def test_structured_data_artifact_round_trip(self) -> None:
        data = {"key": "value", "list": [1, 2, 3], "nested": {"a": True}}
        art = Artifact(artifact_type=ArtifactType.STRUCTURED_DATA, value=data)
        json_str = art.model_dump_json()
        restored = Artifact.model_validate_json(json_str)
        assert restored.value == data

    def test_artifact_with_producer_event_round_trip(self) -> None:
        eid = generate_event_id()
        art = Artifact(
            artifact_type=ArtifactType.TOOL_OUTPUT,
            value="42",
            producer_event_id=eid,
        )
        json_str = art.model_dump_json()
        restored = Artifact.model_validate_json(json_str)
        assert restored.producer_event_id == eid


class TestEventSerialization:
    """Round-trip tests for Event."""

    def test_simple_event_round_trip(self) -> None:
        rid = generate_run_id()
        ts = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        evt = Event(
            run_id=rid,
            event_type=EventType.INPUT,
            timestamp=ts,
            sequence_number=0,
            component="input_handler",
            payload={"text": "What is AI?"},
        )
        json_str = evt.model_dump_json()
        restored = Event.model_validate_json(json_str)
        assert restored.event_id == evt.event_id
        assert restored.run_id == rid
        assert restored.event_type == EventType.INPUT
        assert restored.sequence_number == 0
        assert restored.component == "input_handler"
        assert restored.payload == {"text": "What is AI?"}

    def test_event_with_artifact_refs_round_trip(self) -> None:
        rid = generate_run_id()
        in_art = "art_input1"
        out_art = "art_output1"
        evt = Event(
            run_id=rid,
            event_type=EventType.REASONING,
            sequence_number=1,
            input_artifact_ids=[in_art],
            output_artifact_ids=[out_art],
        )
        json_str = evt.model_dump_json()
        restored = Event.model_validate_json(json_str)
        assert restored.input_artifact_ids == [in_art]
        assert restored.output_artifact_ids == [out_art]

    def test_event_with_parent_round_trip(self) -> None:
        rid = generate_run_id()
        parent_id = generate_event_id()
        evt = Event(
            run_id=rid,
            event_type=EventType.TOOL_RESULT,
            parent_event_id=parent_id,
            sequence_number=2,
        )
        json_str = evt.model_dump_json()
        restored = Event.model_validate_json(json_str)
        assert restored.parent_event_id == parent_id

    def test_event_timestamp_preserved(self) -> None:
        """Timestamp should survive round-trip without losing timezone info."""
        rid = generate_run_id()
        ts = datetime(2026, 7, 4, 18, 30, 45, tzinfo=UTC)
        evt = Event(run_id=rid, event_type=EventType.OUTPUT, timestamp=ts)
        json_str = evt.model_dump_json()
        restored = Event.model_validate_json(json_str)
        assert restored.timestamp == ts


class TestExecutionRunSerialization:
    """Round-trip tests for ExecutionRun."""

    def test_empty_run_round_trip(self) -> None:
        run = ExecutionRun(
            status=RunStatus.CREATED,
            task_input="test task",
        )
        json_str = run.model_dump_json()
        restored = ExecutionRun.model_validate_json(json_str)
        assert restored.run_id == run.run_id
        assert restored.status == RunStatus.CREATED
        assert restored.task_input == "test task"
        assert restored.events == []
        assert restored.artifacts == []

    def test_completed_run_round_trip(self) -> None:
        start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2026, 6, 1, 12, 0, 30, tzinfo=UTC)
        run = ExecutionRun(
            status=RunStatus.COMPLETED,
            started_at=start,
            ended_at=end,
            task_input="Compute 2+2",
            metadata={"experiment_id": "exp_001"},
        )
        json_str = run.model_dump_json()
        restored = ExecutionRun.model_validate_json(json_str)
        assert restored.status == RunStatus.COMPLETED
        assert restored.started_at == start
        assert restored.ended_at == end

    def test_run_with_events_round_trip(self) -> None:
        run = ExecutionRun(task_input="test")
        for i in range(3):
            evt = Event(
                run_id=run.run_id,
                event_type=[EventType.INPUT, EventType.REASONING, EventType.OUTPUT][i],
                sequence_number=i,
                payload={"step": i},
            )
            run.add_event(evt)

        json_str = run.model_dump_json()
        restored = ExecutionRun.model_validate_json(json_str)
        assert restored.event_count == 3
        assert restored.events[0].event_type == EventType.INPUT
        assert restored.events[1].event_type == EventType.REASONING
        assert restored.events[2].event_type == EventType.OUTPUT
        for i, evt in enumerate(restored.events):
            assert evt.sequence_number == i

    def test_run_with_artifacts_round_trip(self) -> None:
        run = ExecutionRun(task_input="test")
        art1 = Artifact(artifact_type=ArtifactType.TEXT, value="input text")
        art2 = Artifact(artifact_type=ArtifactType.MODEL_OUTPUT, value="model response")
        run.add_artifact(art1)
        run.add_artifact(art2)

        json_str = run.model_dump_json()
        restored = ExecutionRun.model_validate_json(json_str)
        assert restored.artifact_count == 2
        assert restored.artifacts[0].artifact_type == ArtifactType.TEXT
        assert restored.artifacts[1].artifact_type == ArtifactType.MODEL_OUTPUT

    def test_full_run_with_linked_events_and_artifacts(self) -> None:
        """A realistic run with events referencing artifacts by ID."""
        run = ExecutionRun(task_input="What is 2+2?", status=RunStatus.RUNNING)

        # Create artifacts
        input_art = Artifact(artifact_type=ArtifactType.TEXT, value="What is 2+2?")
        output_art = Artifact(artifact_type=ArtifactType.MODEL_OUTPUT, value="4")
        run.add_artifact(input_art)
        run.add_artifact(output_art)

        # Create events referencing artifacts by ID
        e0 = Event(
            run_id=run.run_id,
            event_type=EventType.INPUT,
            sequence_number=0,
            output_artifact_ids=[input_art.artifact_id],
        )
        e1 = Event(
            run_id=run.run_id,
            event_type=EventType.REASONING,
            sequence_number=1,
            input_artifact_ids=[input_art.artifact_id],
            output_artifact_ids=[output_art.artifact_id],
        )
        e2 = Event(
            run_id=run.run_id,
            event_type=EventType.OUTPUT,
            sequence_number=2,
            input_artifact_ids=[output_art.artifact_id],
        )
        run.add_event(e0)
        run.add_event(e1)
        run.add_event(e2)

        # Round-trip through JSON string
        json_str = run.model_dump_json()
        data = json.loads(json_str)
        restored = ExecutionRun.model_validate(data)

        assert restored.event_count == 3
        assert restored.artifact_count == 2
        # Verify artifact references survive
        assert restored.events[1].input_artifact_ids == [input_art.artifact_id]
        assert restored.events[1].output_artifact_ids == [output_art.artifact_id]

    def test_parent_run_id_round_trip(self) -> None:
        parent = ExecutionRun()
        child = ExecutionRun(parent_run_id=parent.run_id, task_input="replay")
        json_str = child.model_dump_json()
        restored = ExecutionRun.model_validate_json(json_str)
        assert restored.parent_run_id == parent.run_id

    def test_json_output_is_valid_json(self) -> None:
        """Verify the output is parseable JSON."""
        run = ExecutionRun(task_input="test")
        run.add_event(Event(run_id=run.run_id, event_type=EventType.INPUT))
        json_str = run.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "run_id" in parsed
        assert "events" in parsed
