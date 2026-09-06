"""Tests for captain.models.execution -- ExecutionRun canonical model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_run_id


class TestExecutionRun:
    """Tests for the ExecutionRun model."""

    def test_construction_defaults(self) -> None:
        run = ExecutionRun()
        assert run.run_id.startswith("run_")
        assert run.status == RunStatus.CREATED
        assert run.ended_at is None
        assert run.events == []
        assert run.artifacts == []
        assert run.parent_run_id is None

    def test_explicit_run_id(self) -> None:
        rid = generate_run_id()
        run = ExecutionRun(run_id=rid)
        assert run.run_id == rid

    def test_empty_run_id_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            ExecutionRun(run_id="")

    def test_started_at_is_utc(self) -> None:
        run = ExecutionRun()
        assert run.started_at.tzinfo is not None

    def test_end_before_start_raises(self) -> None:
        start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        end = start - timedelta(hours=1)
        with pytest.raises(ValueError, match="precede"):
            ExecutionRun(started_at=start, ended_at=end)

    def test_valid_end_time(self) -> None:
        start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        end = start + timedelta(seconds=30)
        run = ExecutionRun(started_at=start, ended_at=end)
        assert run.ended_at == end

    def test_task_input(self) -> None:
        run = ExecutionRun(task_input="What is 2+2?")
        assert run.task_input == "What is 2+2?"

    def test_add_event(self) -> None:
        run = ExecutionRun()
        evt = Event(run_id=run.run_id, event_type=EventType.INPUT, sequence_number=0)
        run.add_event(evt)
        assert run.event_count == 1
        assert run.events[0] is evt

    def test_add_event_wrong_run_id_raises(self) -> None:
        run = ExecutionRun()
        evt = Event(run_id="run_other", event_type=EventType.INPUT)
        with pytest.raises(ValueError, match="does not match"):
            run.add_event(evt)

    def test_add_artifact(self) -> None:
        run = ExecutionRun()
        art = Artifact(artifact_type=ArtifactType.TEXT, value="hello")
        run.add_artifact(art)
        assert run.artifact_count == 1
        assert run.artifacts[0] is art

    def test_multiple_events_ordered(self) -> None:
        run = ExecutionRun()
        for i in range(5):
            evt = Event(run_id=run.run_id, event_type=EventType.REASONING, sequence_number=i)
            run.add_event(evt)
        assert run.event_count == 5
        seq_nums = [e.sequence_number for e in run.events]
        assert seq_nums == [0, 1, 2, 3, 4]

    def test_multiple_artifacts(self) -> None:
        run = ExecutionRun()
        for _ in range(3):
            run.add_artifact(Artifact(artifact_type=ArtifactType.TEXT, value="x"))
        assert run.artifact_count == 3

    def test_parent_run_id(self) -> None:
        parent = ExecutionRun()
        child = ExecutionRun(parent_run_id=parent.run_id)
        assert child.parent_run_id == parent.run_id

    def test_status_transitions(self) -> None:
        run = ExecutionRun(status=RunStatus.RUNNING)
        assert run.status == RunStatus.RUNNING
        run.status = RunStatus.COMPLETED
        assert run.status == RunStatus.COMPLETED

    def test_metadata(self) -> None:
        run = ExecutionRun(metadata={"experiment": "baseline_v1"})
        assert run.metadata["experiment"] == "baseline_v1"
