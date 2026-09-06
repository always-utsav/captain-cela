"""Tests for captain.storage.store -- FileTraceStore."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_run_id
from captain.storage.store import FileTraceStore


@pytest.fixture()
def store_dir(tmp_path: Path) -> Path:
    """Provide an isolated temp directory for each test."""
    return tmp_path / "traces"


@pytest.fixture()
def store(store_dir: Path) -> FileTraceStore:
    """Provide a FileTraceStore in an isolated temp directory."""
    return FileTraceStore(store_dir)


def _make_run(
    *,
    task: str = "test task",
    status: RunStatus = RunStatus.COMPLETED,
    run_id: str | None = None,
    started_at: datetime | None = None,
) -> ExecutionRun:
    """Create a minimal ExecutionRun for testing."""
    now = started_at or datetime.now(tz=UTC)
    return ExecutionRun(
        run_id=run_id or generate_run_id(),
        status=status,
        started_at=now,
        ended_at=now if status == RunStatus.COMPLETED else None,
        task_input=task,
    )


class TestFileTraceStoreBasic:
    """Basic CRUD operations."""

    def test_creates_directory(self, store_dir: Path) -> None:
        assert not store_dir.exists()
        FileTraceStore(store_dir)
        assert store_dir.exists()

    def test_save_creates_json_file(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        path = store.base_dir / f"{run.run_id}.json"
        assert path.exists()
        assert path.suffix == ".json"

    def test_load_returns_equivalent_run(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id
        assert loaded.task_input == run.task_input
        assert loaded.status == run.status

    def test_save_load_round_trip_preserves_data(self, store: FileTraceStore) -> None:
        run = _make_run(task="round trip test")
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.model_dump() == run.model_dump()

    def test_load_missing_returns_none(self, store: FileTraceStore) -> None:
        assert store.load("run_nonexistent") is None

    def test_exists_true(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        assert store.exists(run.run_id)

    def test_exists_false(self, store: FileTraceStore) -> None:
        assert not store.exists("run_nonexistent")

    def test_delete_existing(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        assert store.delete(run.run_id)
        assert not store.exists(run.run_id)

    def test_delete_missing_returns_false(self, store: FileTraceStore) -> None:
        assert not store.delete("run_nonexistent")

    def test_count_empty(self, store: FileTraceStore) -> None:
        assert store.count() == 0

    def test_count_multiple(self, store: FileTraceStore) -> None:
        for _ in range(3):
            store.save(_make_run())
        assert store.count() == 3

    def test_list_runs_empty(self, store: FileTraceStore) -> None:
        assert store.list_runs() == []

    def test_list_runs_returns_ids(self, store: FileTraceStore) -> None:
        ids = []
        for _ in range(3):
            run = _make_run()
            store.save(run)
            ids.append(run.run_id)
        listed = store.list_runs()
        assert sorted(listed) == sorted(ids)

    def test_overwrite_replaces_run(self, store: FileTraceStore) -> None:
        run = _make_run(task="original")
        store.save(run)
        run.task_input = "updated"
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.task_input == "updated"
        assert store.count() == 1


class TestFileTraceStoreWithEvents:
    """Tests with events and artifacts attached."""

    def test_round_trip_with_events(self, store: FileTraceStore) -> None:
        from captain.models.events import Event

        run = _make_run()
        run.add_event(
            Event(
                run_id=run.run_id,
                event_type=EventType.INPUT,
                component="agent",
                sequence_number=0,
                payload={"text": "hello"},
            )
        )
        run.add_event(
            Event(
                run_id=run.run_id,
                event_type=EventType.OUTPUT,
                component="agent",
                sequence_number=1,
                payload={"content": "world"},
            )
        )
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.event_count == 2
        assert loaded.events[0].event_type == EventType.INPUT
        assert loaded.events[1].event_type == EventType.OUTPUT

    def test_round_trip_with_artifacts(self, store: FileTraceStore) -> None:
        from captain.models.artifacts import Artifact

        run = _make_run()
        run.add_artifact(Artifact(artifact_type=ArtifactType.TEXT, value="test data"))
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.artifact_count == 1
        assert loaded.artifacts[0].value == "test data"


class TestFileTraceStoreEdgeCases:
    """Edge case and error handling tests."""

    def test_corrupt_json_returns_none(self, store: FileTraceStore) -> None:
        """A file with invalid JSON should return None on load."""
        path = store.base_dir / "run_corrupt.json"
        path.write_text("this is not json", encoding="utf-8")
        assert store.load("run_corrupt") is None

    def test_invalid_model_json_returns_none(self, store: FileTraceStore) -> None:
        """Valid JSON but data failing model validation should return None."""
        path = store.base_dir / "run_invalid.json"
        # run_id="" fails the _run_id_not_empty validator
        path.write_text(
            json.dumps({"run_id": "", "status": "completed"}),
            encoding="utf-8",
        )
        assert store.load("run_invalid") is None

    def test_json_file_is_human_readable(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        path = store.base_dir / f"{run.run_id}.json"
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)
        assert parsed["run_id"] == run.run_id

    def test_stored_json_is_indented(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        path = store.base_dir / f"{run.run_id}.json"
        raw = path.read_text(encoding="utf-8")
        # Indented JSON has newlines and leading spaces
        assert "\n" in raw
        assert "  " in raw

    def test_atomic_write_no_temp_files_left(self, store: FileTraceStore) -> None:
        run = _make_run()
        store.save(run)
        tmp_files = list(store.base_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_non_json_files_ignored_in_list(self, store: FileTraceStore) -> None:
        """Non-.json files in the directory should be ignored."""
        (store.base_dir / "notes.txt").write_text("ignore me")
        run = _make_run()
        store.save(run)
        assert store.list_runs() == [run.run_id]
        assert store.count() == 1

    def test_save_and_load_across_separate_store_instances(self, store_dir: Path) -> None:
        """A second FileTraceStore pointing at the same dir should see the data."""
        store1 = FileTraceStore(store_dir)
        run = _make_run()
        store1.save(run)

        store2 = FileTraceStore(store_dir)
        loaded = store2.load(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id
