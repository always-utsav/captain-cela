"""Execution trace collector for CAPTAIN.

The :class:`TraceCollector` manages the lifecycle of an
:class:`~captain.models.execution.ExecutionRun` during agent execution.
It is responsible for:

- creating the run
- recording canonical :class:`~captain.models.events.Event` objects
- recording canonical :class:`~captain.models.artifacts.Artifact` objects
- assigning monotonically increasing sequence numbers
- tracking run lifecycle (CREATED → RUNNING → COMPLETED/FAILED)
- completing or failing the run

Agent components do **not** construct ``ExecutionRun`` objects directly.
The collector owns all trace bookkeeping.

Usage::

    collector = TraceCollector()
    collector.start_run(task_text="What is 2+2?")

    evt = collector.record_event(EventType.INPUT, component="agent", ...)
    art = collector.record_artifact(ArtifactType.TEXT, value="What is 2+2?", ...)

    collector.complete_run()
    run = collector.get_run()
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_run_id


class TraceCollector:
    """Manages the lifecycle of a single traced execution run.

    Each :class:`TraceCollector` instance is bound to exactly one
    :class:`~captain.models.execution.ExecutionRun`.  Create a new
    collector for each agent execution.

    The collector assigns monotonically increasing sequence numbers
    to events and manages run status transitions.
    """

    def __init__(self) -> None:
        self._run: ExecutionRun | None = None
        self._sequence: int = 0

    # --- lifecycle ----------------------------------------------------------

    def start_run(
        self,
        task_text: str = "",
        *,
        metadata: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> ExecutionRun:
        """Create and start a new execution run.

        Args:
            task_text: The task/prompt that initiated the run.
            metadata: Optional metadata for the run.
            run_id: Optional explicit run ID (auto-generated if omitted).

        Returns:
            The newly created :class:`ExecutionRun` in ``RUNNING`` status.

        Raises:
            RuntimeError: If a run is already active.
        """
        if self._run is not None:
            msg = "A run is already active on this collector"
            raise RuntimeError(msg)

        self._run = ExecutionRun(
            run_id=run_id or generate_run_id(),
            status=RunStatus.RUNNING,
            started_at=datetime.now(tz=UTC),
            task_input=task_text,
            metadata=metadata or {},
        )
        self._sequence = 0
        return self._run

    def complete_run(self) -> ExecutionRun:
        """Mark the current run as completed.

        Returns:
            The completed :class:`ExecutionRun`.

        Raises:
            RuntimeError: If no run is active.
        """
        run = self._require_active_run()
        run.status = RunStatus.COMPLETED
        run.ended_at = datetime.now(tz=UTC)
        return run

    def fail_run(self, error: BaseException | None = None) -> ExecutionRun:
        """Mark the current run as failed.

        If *error* is provided, an ``ERROR`` event is recorded automatically.

        Args:
            error: The exception that caused the failure.

        Returns:
            The failed :class:`ExecutionRun`.

        Raises:
            RuntimeError: If no run is active.
        """
        run = self._require_active_run()
        run.status = RunStatus.FAILED
        run.ended_at = datetime.now(tz=UTC)

        if error is not None:
            self.record_event(
                EventType.ERROR,
                component="agent",
                payload={
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                },
            )
        return run

    def get_run(self) -> ExecutionRun:
        """Return the current run (active or completed).

        Raises:
            RuntimeError: If no run has been started.
        """
        if self._run is None:
            msg = "No run has been started"
            raise RuntimeError(msg)
        return self._run

    @property
    def is_active(self) -> bool:
        """Whether a run is currently in RUNNING status."""
        return self._run is not None and self._run.status == RunStatus.RUNNING

    # --- event recording ----------------------------------------------------

    def record_event(
        self,
        event_type: EventType,
        *,
        component: str = "",
        parent_event_id: str | None = None,
        input_artifact_ids: list[str] | None = None,
        output_artifact_ids: list[str] | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Record a canonical event on the current run.

        Sequence numbers are assigned automatically and increase
        monotonically.

        Args:
            event_type: The category of event.
            component: Logical source component.
            parent_event_id: Optional structural parent event.
            input_artifact_ids: Artifact IDs consumed by this event.
            output_artifact_ids: Artifact IDs produced by this event.
            payload: Structured event-specific data.
            metadata: Additional context.

        Returns:
            The newly created :class:`Event`.

        Raises:
            RuntimeError: If no run is active.
        """
        run = self._require_active_run()

        event = Event(
            run_id=run.run_id,
            event_type=event_type,
            timestamp=datetime.now(tz=UTC),
            sequence_number=self._sequence,
            component=component,
            parent_event_id=parent_event_id,
            input_artifact_ids=input_artifact_ids or [],
            output_artifact_ids=output_artifact_ids or [],
            payload=payload or {},
            metadata=metadata or {},
        )
        run.add_event(event)
        self._sequence += 1
        return event

    # --- artifact recording -------------------------------------------------

    def record_artifact(
        self,
        artifact_type: ArtifactType,
        *,
        value: str | dict[str, Any] | list[Any] | None = None,
        reference: str | None = None,
        producer_event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Record a canonical artifact on the current run.

        Args:
            artifact_type: The kind/modality of data.
            value: Inline data (small payloads).
            reference: URI/path for external/large content.
            producer_event_id: ID of the event that produced this artifact.
            metadata: Additional context.

        Returns:
            The newly created :class:`Artifact`.

        Raises:
            RuntimeError: If no run is active.
        """
        run = self._require_active_run()

        artifact = Artifact(
            artifact_type=artifact_type,
            value=value,
            reference=reference,
            producer_event_id=producer_event_id,
            metadata=metadata or {},
        )
        run.add_artifact(artifact)
        return artifact

    # --- internal -----------------------------------------------------------

    def _require_active_run(self) -> ExecutionRun:
        """Return the active run or raise if none exists."""
        if self._run is None:
            msg = "No run has been started"
            raise RuntimeError(msg)
        return self._run
