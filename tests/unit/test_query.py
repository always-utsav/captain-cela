"""Tests for captain.storage.query -- TraceQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from captain.models.enums import EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_run_id
from captain.storage.query import TraceQuery
from captain.storage.store import FileTraceStore


@pytest.fixture()
def store(tmp_path: Path) -> FileTraceStore:
    """Provide a FileTraceStore in an isolated temp directory."""
    return FileTraceStore(tmp_path / "query_traces")


def _make_run(
    *,
    task: str = "test",
    status: RunStatus = RunStatus.COMPLETED,
    started_at: datetime | None = None,
    event_types: list[EventType] | None = None,
) -> ExecutionRun:
    """Create a run with optional events for testing."""
    now = started_at or datetime.now(tz=UTC)
    run = ExecutionRun(
        run_id=generate_run_id(),
        status=status,
        started_at=now,
        ended_at=now if status in (RunStatus.COMPLETED, RunStatus.FAILED) else None,
        task_input=task,
    )
    for i, et in enumerate(event_types or []):
        run.add_event(
            Event(
                run_id=run.run_id,
                event_type=et,
                sequence_number=i,
                component="test",
            )
        )
    return run


class TestTraceQueryByStatus:
    """Tests for status filtering."""

    def test_filter_completed(self, store: FileTraceStore) -> None:
        r1 = _make_run(status=RunStatus.COMPLETED)
        r2 = _make_run(status=RunStatus.FAILED)
        store.save(r1)
        store.save(r2)

        results = TraceQuery(store).by_status(RunStatus.COMPLETED).execute()
        assert len(results) == 1
        assert results[0].run_id == r1.run_id

    def test_filter_failed(self, store: FileTraceStore) -> None:
        r1 = _make_run(status=RunStatus.COMPLETED)
        r2 = _make_run(status=RunStatus.FAILED)
        store.save(r1)
        store.save(r2)

        results = TraceQuery(store).by_status(RunStatus.FAILED).execute()
        assert len(results) == 1
        assert results[0].run_id == r2.run_id

    def test_no_match_returns_empty(self, store: FileTraceStore) -> None:
        store.save(_make_run(status=RunStatus.COMPLETED))
        results = TraceQuery(store).by_status(RunStatus.CANCELLED).execute()
        assert results == []


class TestTraceQueryByRunId:
    """Tests for run ID filtering."""

    def test_find_by_id(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        results = TraceQuery(store).by_run_id(run.run_id).execute()
        assert len(results) == 1
        assert results[0].run_id == run.run_id

    def test_missing_id_returns_empty(self, store: FileTraceStore) -> None:
        results = TraceQuery(store).by_run_id("run_missing").execute()
        assert results == []


class TestTraceQueryByTimeRange:
    """Tests for time range filtering."""

    def test_filter_by_start_time(self, store: FileTraceStore) -> None:
        t1 = datetime(2026, 1, 1, tzinfo=UTC)
        t2 = datetime(2026, 6, 1, tzinfo=UTC)
        t3 = datetime(2026, 12, 1, tzinfo=UTC)

        r1 = _make_run(started_at=t1)
        r2 = _make_run(started_at=t2)
        r3 = _make_run(started_at=t3)
        store.save(r1)
        store.save(r2)
        store.save(r3)

        # Filter: after Feb 1 and before Nov 1
        results = (
            TraceQuery(store)
            .by_time_range(
                start=datetime(2026, 2, 1, tzinfo=UTC),
                end=datetime(2026, 11, 1, tzinfo=UTC),
            )
            .execute()
        )
        assert len(results) == 1
        assert results[0].run_id == r2.run_id

    def test_open_ended_range(self, store: FileTraceStore) -> None:
        t1 = datetime(2025, 1, 1, tzinfo=UTC)
        t2 = datetime(2026, 1, 1, tzinfo=UTC)

        store.save(_make_run(started_at=t1))
        store.save(_make_run(started_at=t2))

        results = TraceQuery(store).by_time_range(start=datetime(2025, 6, 1, tzinfo=UTC)).execute()
        assert len(results) == 1

    def test_open_start_range(self, store: FileTraceStore) -> None:
        t1 = datetime(2025, 1, 1, tzinfo=UTC)
        t2 = datetime(2026, 1, 1, tzinfo=UTC)

        store.save(_make_run(started_at=t1))
        store.save(_make_run(started_at=t2))

        results = TraceQuery(store).by_time_range(end=datetime(2025, 6, 1, tzinfo=UTC)).execute()
        assert len(results) == 1


class TestTraceQueryByEventType:
    """Tests for event type filtering."""

    def test_filter_by_tool_call(self, store: FileTraceStore) -> None:
        r1 = _make_run(event_types=[EventType.INPUT, EventType.TOOL_CALL, EventType.OUTPUT])
        r2 = _make_run(event_types=[EventType.INPUT, EventType.OUTPUT])
        store.save(r1)
        store.save(r2)

        results = TraceQuery(store).by_event_type(EventType.TOOL_CALL).execute()
        assert len(results) == 1
        assert results[0].run_id == r1.run_id

    def test_no_matching_event_type(self, store: FileTraceStore) -> None:
        store.save(_make_run(event_types=[EventType.INPUT]))
        results = TraceQuery(store).by_event_type(EventType.ERROR).execute()
        assert results == []


class TestTraceQueryComposed:
    """Tests for chaining multiple filters."""

    def test_status_and_event_type(self, store: FileTraceStore) -> None:
        r1 = _make_run(
            status=RunStatus.COMPLETED,
            event_types=[EventType.TOOL_CALL],
        )
        r2 = _make_run(
            status=RunStatus.FAILED,
            event_types=[EventType.TOOL_CALL],
        )
        r3 = _make_run(
            status=RunStatus.COMPLETED,
            event_types=[EventType.INPUT],
        )
        store.save(r1)
        store.save(r2)
        store.save(r3)

        results = (
            TraceQuery(store)
            .by_status(RunStatus.COMPLETED)
            .by_event_type(EventType.TOOL_CALL)
            .execute()
        )
        assert len(results) == 1
        assert results[0].run_id == r1.run_id

    def test_first_returns_match(self, store: FileTraceStore) -> None:
        store.save(_make_run())
        result = TraceQuery(store).by_status(RunStatus.COMPLETED).first()
        assert result is not None

    def test_first_returns_none_on_no_match(self, store: FileTraceStore) -> None:
        result = TraceQuery(store).by_status(RunStatus.COMPLETED).first()
        assert result is None

    def test_results_sorted_by_started_at(self, store: FileTraceStore) -> None:
        t1 = datetime(2026, 3, 1, tzinfo=UTC)
        t2 = datetime(2026, 1, 1, tzinfo=UTC)
        t3 = datetime(2026, 2, 1, tzinfo=UTC)

        store.save(_make_run(started_at=t1))
        store.save(_make_run(started_at=t2))
        store.save(_make_run(started_at=t3))

        results = TraceQuery(store).execute()
        assert len(results) == 3
        assert results[0].started_at <= results[1].started_at <= results[2].started_at

    def test_empty_query_returns_all(self, store: FileTraceStore) -> None:
        for _ in range(4):
            store.save(_make_run())
        results = TraceQuery(store).execute()
        assert len(results) == 4
