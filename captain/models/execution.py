"""Canonical execution run model for CAPTAIN.

An :class:`ExecutionRun` represents one complete agent execution.  It
aggregates an ordered collection of :class:`~captain.models.events.Event`
objects and associated :class:`~captain.models.artifacts.Artifact` objects.

The ``parent_run_id`` field supports future counterfactual/replay
relationships without implementing replay logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from captain.models.artifacts import Artifact
from captain.models.enums import RunStatus
from captain.models.events import Event
from captain.models.ids import generate_run_id


class ExecutionRun(BaseModel):
    """Canonical representation of one complete agent execution.

    Attributes:
        run_id: Globally unique identifier (``run_`` prefix).
        status: Current lifecycle status of the run.
        started_at: Timezone-aware UTC start timestamp.
        ended_at: Timezone-aware UTC end timestamp (set on completion/failure).
        task_input: The textual or structured task that initiated the run.
        events: Ordered list of events recorded during execution.
        artifacts: Collection of artifacts produced/consumed during execution.
        metadata: Additional key/value context.
        parent_run_id: Optional ID of a parent run for counterfactual/replay
            relationships (future use -- not implemented).
    """

    run_id: str = Field(default_factory=generate_run_id)
    status: RunStatus = RunStatus.CREATED
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=__import__("datetime").UTC)
    )
    ended_at: datetime | None = None
    task_input: str = ""
    events: list[Event] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_run_id: str | None = None

    # --- validators ---------------------------------------------------------

    @field_validator("run_id")
    @classmethod
    def _run_id_not_empty(cls, v: str) -> str:
        if not v:
            msg = "run_id must not be empty"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _validate_timestamps(self) -> ExecutionRun:
        """Ensure ended_at does not precede started_at."""
        if self.ended_at is not None and self.ended_at < self.started_at:
            msg = "ended_at must not precede started_at"
            raise ValueError(msg)
        return self

    # --- convenience helpers ------------------------------------------------

    def add_event(self, event: Event) -> None:
        """Append an event to the run, verifying it references this run."""
        if event.run_id != self.run_id:
            msg = f"Event run_id '{event.run_id}' does not match run '{self.run_id}'"
            raise ValueError(msg)
        self.events.append(event)

    def add_artifact(self, artifact: Artifact) -> None:
        """Append an artifact to the run."""
        self.artifacts.append(artifact)

    @property
    def event_count(self) -> int:
        """Number of events in this run."""
        return len(self.events)

    @property
    def artifact_count(self) -> int:
        """Number of artifacts in this run."""
        return len(self.artifacts)

    @field_serializer("started_at", "ended_at")
    @classmethod
    def _serialize_datetime(cls, v: datetime | None) -> str | None:
        return v.isoformat() if v is not None else None
