"""Tests for captain.tracing.collector -- TraceCollector."""

from __future__ import annotations

import pytest

from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.tracing.collector import TraceCollector


class TestTraceCollectorLifecycle:
    """Tests for run creation and lifecycle transitions."""

    def test_start_run_creates_running_run(self) -> None:
        tc = TraceCollector()
        run = tc.start_run(task_text="hello")
        assert run.status == RunStatus.RUNNING
        assert run.task_input == "hello"
        assert run.run_id.startswith("run_")
        assert tc.is_active

    def test_start_run_with_metadata(self) -> None:
        tc = TraceCollector()
        run = tc.start_run(metadata={"key": "val"})
        assert run.metadata["key"] == "val"

    def test_start_run_with_explicit_id(self) -> None:
        tc = TraceCollector()
        run = tc.start_run(run_id="run_custom123")
        assert run.run_id == "run_custom123"

    def test_start_run_twice_raises(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        with pytest.raises(RuntimeError, match="already active"):
            tc.start_run()

    def test_complete_run(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        run = tc.complete_run()
        assert run.status == RunStatus.COMPLETED
        assert run.ended_at is not None
        assert run.ended_at >= run.started_at
        assert not tc.is_active

    def test_fail_run(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        run = tc.fail_run()
        assert run.status == RunStatus.FAILED
        assert run.ended_at is not None
        assert not tc.is_active

    def test_fail_run_with_error_records_error_event(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        run = tc.fail_run(error=ValueError("test error"))
        error_events = [e for e in run.events if e.event_type == EventType.ERROR]
        assert len(error_events) == 1
        assert error_events[0].payload["error_type"] == "ValueError"
        assert error_events[0].payload["error_message"] == "test error"

    def test_get_run_before_start_raises(self) -> None:
        tc = TraceCollector()
        with pytest.raises(RuntimeError, match="No run"):
            tc.get_run()

    def test_get_run_returns_run(self) -> None:
        tc = TraceCollector()
        tc.start_run(task_text="x")
        run = tc.get_run()
        assert run.task_input == "x"

    def test_complete_without_start_raises(self) -> None:
        tc = TraceCollector()
        with pytest.raises(RuntimeError, match="No run"):
            tc.complete_run()

    def test_timestamps_are_utc(self) -> None:
        tc = TraceCollector()
        run = tc.start_run()
        assert run.started_at.tzinfo is not None
        tc.complete_run()
        assert run.ended_at is not None
        assert run.ended_at.tzinfo is not None


class TestTraceCollectorEvents:
    """Tests for event recording."""

    def test_record_event_basic(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        evt = tc.record_event(EventType.INPUT, component="agent")
        assert evt.event_type == EventType.INPUT
        assert evt.component == "agent"
        assert evt.event_id.startswith("evt_")
        run = tc.get_run()
        assert run.event_count == 1

    def test_monotonic_sequence_numbers(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        e0 = tc.record_event(EventType.INPUT)
        e1 = tc.record_event(EventType.PLANNING)
        e2 = tc.record_event(EventType.REASONING)
        e3 = tc.record_event(EventType.OUTPUT)
        assert e0.sequence_number == 0
        assert e1.sequence_number == 1
        assert e2.sequence_number == 2
        assert e3.sequence_number == 3

    def test_event_run_id_matches(self) -> None:
        tc = TraceCollector()
        run = tc.start_run()
        evt = tc.record_event(EventType.INPUT)
        assert evt.run_id == run.run_id

    def test_event_with_payload(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        evt = tc.record_event(EventType.INPUT, payload={"text": "hello"})
        assert evt.payload["text"] == "hello"

    def test_event_with_metadata(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        evt = tc.record_event(EventType.INPUT, metadata={"source": "test"})
        assert evt.metadata["source"] == "test"

    def test_event_with_parent(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        parent = tc.record_event(EventType.TOOL_CALL, component="tool:calc")
        child = tc.record_event(
            EventType.TOOL_RESULT,
            component="tool:calc",
            parent_event_id=parent.event_id,
        )
        assert child.parent_event_id == parent.event_id

    def test_event_with_artifact_ids(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        art = tc.record_artifact(ArtifactType.TEXT, value="hello")
        evt = tc.record_event(
            EventType.INPUT,
            output_artifact_ids=[art.artifact_id],
        )
        assert art.artifact_id in evt.output_artifact_ids

    def test_record_event_without_active_run_raises(self) -> None:
        tc = TraceCollector()
        with pytest.raises(RuntimeError, match="No run"):
            tc.record_event(EventType.INPUT)

    def test_event_timestamps_are_utc(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        evt = tc.record_event(EventType.INPUT)
        assert evt.timestamp.tzinfo is not None


class TestTraceCollectorArtifacts:
    """Tests for artifact recording."""

    def test_record_text_artifact(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        art = tc.record_artifact(ArtifactType.TEXT, value="hello")
        assert art.artifact_type == ArtifactType.TEXT
        assert art.value == "hello"
        assert art.artifact_id.startswith("art_")
        run = tc.get_run()
        assert run.artifact_count == 1

    def test_record_image_artifact_by_reference(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        art = tc.record_artifact(ArtifactType.IMAGE, reference="s3://bucket/img.png")
        assert art.reference == "s3://bucket/img.png"
        assert art.value is None

    def test_record_artifact_with_producer(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        evt = tc.record_event(EventType.INPUT)
        art = tc.record_artifact(
            ArtifactType.TEXT,
            value="x",
            producer_event_id=evt.event_id,
        )
        assert art.producer_event_id == evt.event_id

    def test_record_artifact_without_active_run_raises(self) -> None:
        tc = TraceCollector()
        with pytest.raises(RuntimeError, match="No run"):
            tc.record_artifact(ArtifactType.TEXT, value="x")

    def test_multiple_artifacts(self) -> None:
        tc = TraceCollector()
        tc.start_run()
        for _ in range(5):
            tc.record_artifact(ArtifactType.TEXT, value="x")
        assert tc.get_run().artifact_count == 5
